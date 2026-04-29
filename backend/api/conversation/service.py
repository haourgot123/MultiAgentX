from time import time_ns
from typing import Optional, List
from datetime import datetime, timezone
import json
import re
import uuid

from fastapi import Request
from loguru import logger
from sqlalchemy.orm import Session, selectinload

from backend.api.conversation.model import (
    Conversation,
    ConversationCreateRequest,
    ConversationFilesUpdateRequest,
    ConversationMessage,
    ConversationMessageCreateRequest,
    ConversationRenameRequest,
    RetrievalRecord,
    conversation_files,
)
from backend.api.files.model import StoredFile
from backend.api.conversation.model import DeepResearchPlanResponse
from backend.databases.db import get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.utils.constants import Message
from backend.agents.general_agent.state import GeneralAgentState, Tag
from backend.agents.general_agent.graph import GeneralAgentGraph
from backend.agents.deep_research_agent.state import DeepResearchAgentState
from backend.agents.deep_research_agent.graph import DeepResearchAgentGraph
from backend.agents.rag_agent.state import RAGAgentState
from backend.agents.rag_agent.state import Tag as RAGTag
from backend.agents.rag_agent.graph import RAGAgentGraph
from backend.memory.mem0_client import mem0_client
from backend.utils.research_session import research_session_manager
from backend.utils.retention import mark_for_retention_delete



class ConversationService:
    NUMERIC_CITATION_REGEX = re.compile(r"\[(\d+)\](?!\()")
    SOURCES_SECTION_REGEX = re.compile(
        r"(?:^|\n)((?:#{1,6}\s+)?(?:\d+(?:\.\d+)*\.?\s+)?(?:Sources|References|Nguon|Nguồn|Tai lieu tham khao|Tài liệu tham khảo):?\s*$)",
        re.IGNORECASE | re.MULTILINE,
    )
    SOURCES_LINE_REGEX = re.compile(
        r"^\s*(?:\[(\d+)\]|(\d+)\.)\s+",
        re.MULTILINE,
    )

    @staticmethod
    def _get_request_logger(request: Request | None = None, user_id: int | None = None):
        return logger.bind(
            request_id=getattr(getattr(request, "state", None), "request_id", "-"),
            user_id=user_id
            if user_id is not None
            else getattr(getattr(request, "state", None), "user_id", "-"),
        )

    @staticmethod
    def _build_default_title(created_at) -> str:
        return f"New Conversation - {created_at.strftime('%d/%m/%Y %H:%M')}"

    @classmethod
    def _normalize_title(cls, title: Optional[str], created_at=None) -> str:
        if not title or not title.strip():
            if created_at is None:
                created_at = get_utc_now()
            return cls._build_default_title(created_at)
        return title.strip()[:255]

    @classmethod
    def _sanitize_orphan_numeric_citations(cls, content: str) -> str:
        if not content:
            return content

        section_match = cls.SOURCES_SECTION_REGEX.search(content)
        if section_match:
            section_start = section_match.start(1)
            body = content[:section_start]
            sources_section = content[section_start:]
            available_labels = {
                match.group(1) or match.group(2)
                for match in cls.SOURCES_LINE_REGEX.finditer(sources_section)
            }
        else:
            body = content
            sources_section = ""
            available_labels = set()

        def replace_orphan_citation(match: re.Match[str]) -> str:
            if match.group(1) in available_labels:
                return match.group(0)

            previous_char = body[match.start() - 1] if match.start() > 0 else ""
            next_char = body[match.end()] if match.end() < len(body) else ""

            if (
                previous_char
                and next_char
                and not previous_char.isspace()
                and not next_char.isspace()
            ):
                return " "

            return ""

        cleaned_body = cls.NUMERIC_CITATION_REGEX.sub(replace_orphan_citation, body)
        cleaned_body = re.sub(r"[ \t]{2,}", " ", cleaned_body)
        cleaned_body = re.sub(r"[ \t]+([,.;:!?])", r"\1", cleaned_body)
        cleaned_body = re.sub(r"[ \t]+\n", "\n", cleaned_body)

        return f"{cleaned_body}{sources_section}"

    def _get_user_conversation(
        self,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        request_logger,
    ) -> Conversation:
        conversation = (
            db_session.query(Conversation)
            .options(
                selectinload(Conversation.files),
                selectinload(Conversation.messages),
            )
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .first()
        )
        if not conversation:
            request_logger.warning("Conversation not found")
            raise ObjectNotFoundException(message=Message.MESSAGE_CONVERSATION_NOT_FOUND)
        return conversation

    def list_conversations(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        chat_type: Optional[str] = None,
    ) -> list[Conversation]:
        request_logger = self._get_request_logger(request, user_id)
        query = (
            db_session.query(Conversation)
            .options(
                selectinload(Conversation.files),
                selectinload(Conversation.messages),
            )
            .filter(
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
        )
        if chat_type:
            query = query.filter(Conversation.chat_type == chat_type)

        conversations = query.order_by(Conversation.updated_at.desc()).all()
        request_logger.debug(
            "Listed conversations chat_type={} count={}",
            chat_type,
            len(conversations),
        )
        return conversations

    @staticmethod
    def _get_active_files_by_ids(
        db_session: Session,
        user_id: int,
        file_ids: list[int],
    ) -> list[StoredFile]:
        if not file_ids:
            return []

        files = (
            db_session.query(StoredFile)
            .filter(
                StoredFile.user_id == user_id,
                StoredFile.deleted_at.is_(None),
                StoredFile.id.in_(file_ids),
            )
            .all()
        )
        files_by_id = {file.id: file for file in files}
        if len(files_by_id) != len(set(file_ids)):
            raise InvalidRequestException(message=Message.MESSAGE_FILE_NOT_FOUND)

        ordered_files: list[StoredFile] = []
        seen_ids: set[int] = set()
        for file_id in file_ids:
            if file_id in seen_ids:
                continue
            ordered_files.append(files_by_id[file_id])
            seen_ids.add(file_id)
        return ordered_files

    def create_conversation(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        create_request: ConversationCreateRequest,
    ) -> Conversation:
        request_logger = self._get_request_logger(request, user_id)
        now = get_utc_now()
        if create_request.chat_type == "file":
            conversation_title = self._build_default_title(now)
        else:
            conversation_title = self._normalize_title(create_request.title, now)

        conversation = Conversation(
            user_id=user_id,
            title=conversation_title,
            chat_type=create_request.chat_type,
            created_at=now,
            updated_at=now,
        )

        if create_request.file_ids:
            files = self._get_active_files_by_ids(
                db_session,
                user_id,
                create_request.file_ids,
            )
            conversation.files = files
            request_logger.debug("Creating file conversation with file_count={}", len(files))

        db_session.add(conversation)
        db_session.commit()
        db_session.refresh(conversation)
        request_logger.info(
            "Created conversation id={} type={}",
            conversation.id,
            conversation.chat_type,
        )

        return self._get_user_conversation(
            db_session, user_id, conversation.id, request_logger
        )

    def get_conversation(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        request_logger = self._get_request_logger(request, user_id)
        request_logger.debug("Retrieving conversation")
        return self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )

    def rename_conversation(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        rename_request: ConversationRenameRequest,
    ) -> Conversation:
        request_logger = self._get_request_logger(request, user_id)
        conversation = self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )
        conversation.title = self._normalize_title(rename_request.title)
        conversation.updated_at = get_utc_now()
        db_session.commit()
        db_session.refresh(conversation)
        request_logger.info("Renamed conversation to '{}'", conversation.title)
        return self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )

    def delete_conversation(
        self, request: Request, db_session: Session, user_id: int, conversation_id: int
    ) -> dict:
        request_logger = self._get_request_logger(request, user_id)
        conversation = self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )
        now = get_utc_now()
        mark_for_retention_delete(conversation, now)
        db_session.commit()
        request_logger.info("Soft deleted conversation")
        return {"message": Message.MESSAGE_CONVERSATION_DELETED_SUCCESSFULLY}

    def update_conversation_files(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        files_request: ConversationFilesUpdateRequest,
    ) -> Conversation:
        request_logger = self._get_request_logger(request, user_id)
        conversation = self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )
        if conversation.chat_type != "file":
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_REQUEST)

        current_file_ids = [file.id for file in conversation.files]
        requested_file_ids = list(dict.fromkeys(files_request.file_ids))
        missing_current_ids = [
            file_id for file_id in current_file_ids if file_id not in requested_file_ids
        ]
        if missing_current_ids:
            raise InvalidRequestException(
                message="Files already attached to this conversation cannot be removed."
            )

        files = self._get_active_files_by_ids(
            db_session,
            user_id,
            requested_file_ids,
        )
        conversation.files = files
        conversation.updated_at = get_utc_now()
        db_session.commit()
        db_session.refresh(conversation)
        request_logger.info("Updated conversation files, file_count={}", len(files))
        return self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )

    def add_message(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        message_request: ConversationMessageCreateRequest,
    ) -> tuple[ConversationMessage, Conversation]:
        request_logger = self._get_request_logger(request, user_id)
        conversation = self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )
        now = get_utc_now()

        message = ConversationMessage(
            conversation_id=conversation.id,
            role=message_request.role,
            content=message_request.content.strip(),
            blob_path=message_request.blob_path,
            blob_name=message_request.blob_name,
            blob_content_type=message_request.blob_content_type,
            blob_size=message_request.blob_size,
            created_at=now,
            updated_at=now,
        )
        db_session.add(message)

        conversation.updated_at = now

        db_session.commit()
        db_session.refresh(message)
        updated_conversation = self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )
        request_logger.info("Added message id={} role={}", message.id, message.role)
        return message, updated_conversation
    
    @staticmethod
    def _format_sse_event(event: str, data: dict) -> str:
        """
        Format a Server-Sent Events (SSE) line with JSON data.
        """
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def normal_chat(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        user_question: str,
        is_web_search_enabled: Optional[bool] = False,
        is_deep_research_enabled: Optional[bool] = False,
        is_generate_image_enabled: Optional[bool] = False,
        route_preference: Optional[str] = "auto",
    ):
        request_logger = self._get_request_logger(request, user_id)
        conversation = self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )
        #  Create chat details
        _, _ = self.add_message(
            request,
            db_session,
            user_id,
            conversation_id,
            ConversationMessageCreateRequest(role="user", content=user_question),
        )
        
        if conversation.chat_type != "normal":
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_REQUEST)
        
        # Get last 10 messages from conversation
        messages = conversation.messages[-10:] if len(conversation.messages) > 10 else conversation.messages
        time_now = get_utc_now().strftime("%Y-%m-%d %H:%M:%S")
        # Initialize general agent state
        state = GeneralAgentState(
            conversation_id=conversation_id,
            user_id=user_id,
            memories=messages,
            user_question=user_question,
            time_now=time_now,
            is_web_search_enabled=is_web_search_enabled,
            is_deep_research_enabled=is_deep_research_enabled,
            is_generate_image_enabled=is_generate_image_enabled,
            route_preference=route_preference or "auto",
            websearch_results=[],
            route="",
        )
        
        # We need to collect the chunks to save the assistant's final response to the database
        full_response = ""
        
        # Initialize general agent graph
        try: 
            graph = GeneralAgentGraph()
            async for event in graph.stream(
                state.model_dump()
            ):
                event_type = event.get("type")

                # Stream token chunks to client
                if event_type == "token":
                    delta = event.get("delta", "")
                    if not delta:
                        continue
                    full_response += delta
                    yield self._format_sse_event("token", {"delta": delta})

                # Stream status updates
                elif event_type == "status":
                    payload = {
                        "step": event.get("step"),
                        "message": event.get("message", ""),
                    }
                    yield self._format_sse_event("status", payload)
                
            # After successful generation, store assistant message
            if full_response:
                full_response = self._sanitize_orphan_numeric_citations(full_response)
                _, _ = self.add_message(
                    request,
                    db_session,
                    user_id,
                    conversation_id,
                    ConversationMessageCreateRequest(
                        role="assistant",
                        content=full_response,
                    ),
                )
                
                # NEW: Store conversation in Mem0 for long-term memory
                try:
                    request_logger.info("Storing conversation in Mem0 long-term memory")
                    
                    messages_for_mem0 = [
                        {"role": "user", "content": user_question},
                        {"role": "assistant", "content": full_response}
                    ]
                    
                    await mem0_client.add_memory(
                        messages=messages_for_mem0,
                        user_id=str(user_id),
                        metadata={
                            "conversation_id": conversation_id,
                            "chat_type": conversation.chat_type,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "route": state.route,
                        }
                    )
                    
                    request_logger.debug("Successfully stored memory in Mem0 (Milvus)")
                    
                except Exception as e:
                    # Graceful degradation - don't fail the request
                    request_logger.error(f"Failed to store memory in Mem0: {e}")
                    # Continue execution
                
                # Notify client that streaming is done
                yield self._format_sse_event("done", {"output": full_response})

        except Exception as e:
            request_logger.error("Error streaming general agent: {}", e)
            error_assistant_message = Message.MESSAGE_GENERAL_AGENT_ERROR
            _, _ = self.add_message(
                request,
                db_session,
                user_id,
                conversation_id,
                ConversationMessageCreateRequest(
                    role="assistant",
                    content=error_assistant_message,
                ),
            )
            yield self._format_sse_event(
                "error", {"message": error_assistant_message}
            )
            
        finally:
            del graph
            
    async def file_chat(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        user_question: str,
        file_ids: Optional[List[int]] = None,
    ):
        """Chat with uploaded files using RAG agent with evaluation loop."""
        request_logger = self._get_request_logger(request, user_id)
        conversation = self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )

        if conversation.chat_type != "file":
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_REQUEST)

        # Get file IDs from conversation
        conversation_file_ids = [file.id for file in conversation.files]
        if not conversation_file_ids:
            raise InvalidRequestException(
                message="No files attached to this conversation. Please upload files first."
            )
        requested_file_ids = list(dict.fromkeys(file_ids or conversation_file_ids))
        invalid_file_ids = [
            file_id for file_id in requested_file_ids if file_id not in conversation_file_ids
        ]
        if invalid_file_ids:
            raise InvalidRequestException(
                message="One or more selected files do not belong to this conversation."
            )

        # Save user message
        _, _ = self.add_message(
            request,
            db_session,
            user_id,
            conversation_id,
            ConversationMessageCreateRequest(role="user", content=user_question),
        )

        # Get conversation history for context
        messages = (
            conversation.messages[-10:]
            if len(conversation.messages) > 10
            else conversation.messages
        )

        # Initialize RAG agent state
        rag_state = RAGAgentState(
            user_question=user_question,
            memories=messages,
            user_id=user_id,
            conversation_id=conversation_id,
            file_ids=requested_file_ids,
        )

        full_response = ""
        final_state = {}

        try:
            graph = RAGAgentGraph()
            config = graph._config_graph()

            async for event in graph.compiled_graph.astream_events(
                input=rag_state.model_dump(),
                config=config,
                version="v2",
            ):
                kind = event["event"]
                tags = event.get("tags", [])

                # Real-time LLM token streaming from SynthesizeNode
                if (
                    kind == "on_chat_model_stream"
                    and RAGTag.streaming_node.name in tags
                ):
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        delta = chunk.content
                        full_response += delta
                        yield self._format_sse_event("token", {"delta": delta})

                # Status updates from all nodes
                elif kind == "on_custom_event":
                    event_name = event.get("name", "")
                    event_data = event.get("data", {})

                    if event_name == "status":
                        msg = event_data.get("message", "")
                        if msg:
                            yield self._format_sse_event(
                                "status",
                                {
                                    "step": event_data.get("step"),
                                    "message": msg,
                                },
                            )

                # Capture final graph state for retrieval records
                if kind == "on_chain_end" and event.get("name") == "LangGraph":
                    final_state = event.get("data", {}).get("output", {})

            # Save assistant message
            assistant_message = None
            if full_response:
                full_response = self._sanitize_orphan_numeric_citations(full_response)
                msg_obj, _ = self.add_message(
                    request,
                    db_session,
                    user_id,
                    conversation_id,
                    ConversationMessageCreateRequest(
                        role="assistant",
                        content=full_response,
                    ),
                )
                assistant_message = msg_obj
                request_logger.info("Saved RAG assistant message")

            # Persist retrieval records for PDF bbox highlighting
            citation_map = final_state.get("citation_map", {})
            if assistant_message and citation_map:
                try:
                    self._save_retrieval_records(
                        db_session=db_session,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message_id=assistant_message.id,
                        citation_map=citation_map,
                    )
                    request_logger.info(
                        f"Saved {len(citation_map)} retrieval records"
                    )
                except Exception as e:
                    request_logger.error(
                        f"Failed to save retrieval records: {e}"
                    )

            # Send citations data to FE in the done event
            citations_payload = []
            for label, data in citation_map.items():
                if isinstance(data, dict):
                    citations_payload.append({
                        "citation_label": label,
                        "file_id": data.get("file_id"),
                        "file_name": data.get("file_name", ""),
                        "page_no": data.get("page_no"),
                        "chunk_index": data.get("chunk_index", 0),
                    })

            yield self._format_sse_event(
                "done",
                {
                    "output": full_response,
                    "citations": citations_payload,
                },
            )

        except Exception as e:
            request_logger.error("Error in file_chat RAG agent: {}", e)
            error_message = Message.MESSAGE_GENERAL_AGENT_ERROR
            _, _ = self.add_message(
                request,
                db_session,
                user_id,
                conversation_id,
                ConversationMessageCreateRequest(
                    role="assistant",
                    content=error_message,
                ),
            )
            yield self._format_sse_event(
                "error", {"message": error_message}
            )
        finally:
            if "graph" in locals():
                del graph

    @staticmethod
    def _save_retrieval_records(
        db_session: Session,
        user_id: int,
        conversation_id: int,
        message_id: int,
        citation_map: dict,
    ) -> None:
        """Persist retrieval results to RetrievalRecord table for FE bbox highlighting."""
        now = get_utc_now()
        records = []
        for citation_label, data in citation_map.items():
            if not isinstance(data, dict):
                continue
            record = RetrievalRecord(
                conversation_id=conversation_id,
                message_id=message_id,
                user_id=user_id,
                chunk_id=data.get("chunk_id", ""),
                file_id=data.get("file_id", 0),
                file_name=data.get("file_name"),
                chunk_index=data.get("chunk_index", 0),
                citation_label=citation_label,
                page_no=data.get("page_no"),
                bbox_json=data.get("bbox_json"),
                chunk_text=data.get("chunk_text"),
                relevance_score=data.get("relevance_score"),
                created_at=now,
                updated_at=now,
            )
            records.append(record)

        if records:
            db_session.add_all(records)
            db_session.commit()

    async def create_deep_research_plan(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        user_question: str,
    ) -> DeepResearchPlanResponse:
        """Create a research plan for deep research"""
        request_logger = self._get_request_logger(request, user_id)
        conversation = self._get_user_conversation(
            db_session, user_id, conversation_id, request_logger
        )
        
        if conversation.chat_type != "normal":
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_REQUEST)
        
        # Get last 10 messages from conversation
        messages = conversation.messages[-10:] if len(conversation.messages) > 10 else conversation.messages
        
        # Initialize deep research agent state
        research_state = DeepResearchAgentState(
            user_question=user_question,
            memories=messages,
            max_iterations=3,
        )
        
        # Create plan using DeepResearchAgentGraph in plan_only mode
        try:
            graph = DeepResearchAgentGraph(plan_only=True)
            config = graph._config_graph()
            plan_result = None
            
            # Use astream_events to capture plan_request custom events
            async for event in graph.compiled_graph.astream_events(
                input=research_state.model_dump(),
                config=config,
                version="v2",
            ):
                if event["event"] == "on_custom_event" and event.get("name") == "plan_request":
                    plan_result = event.get("data", {})
                    break
            
            if not plan_result or "plan" not in plan_result:
                raise InvalidRequestException(message="Failed to generate research plan")
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Save session
            research_session_manager.create_session(
                session_id=session_id,
                user_id=user_id,
                conversation_id=conversation_id,
                user_question=user_question,
                memories=[str(m) for m in messages],
                research_plan=plan_result["plan"],
            )
            
            return DeepResearchPlanResponse(
                session_id=session_id,
                plan=plan_result["plan"],
                message=plan_result.get("message", "Research plan created. Please review and approve."),
            )
            
        except Exception as e:
            request_logger.error(f"Error creating research plan: {e}")
            raise InvalidRequestException(message=f"Failed to create research plan: {str(e)}")
        finally:
            if 'graph' in locals():
                del graph

    async def approve_deep_research_plan(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        session_id: str,
        approved_plan: List[str],
    ):
        """Execute deep research with approved plan — uses astream_events directly
        for real-time token streaming from the SynthesizeNode's LLM."""
        request_logger = self._get_request_logger(request, user_id)
        
        # Emit starting research event
        yield self._format_sse_event("status", {
            "step": "deep_research_start",
            "message": "Starting research with approved plan...",
        })
        
        # Get session
        session = research_session_manager.get_session(session_id)
        if not session:
            raise InvalidRequestException(message="Research session not found or expired")
        
        if session["user_id"] != user_id:
            raise InvalidRequestException(message="Unauthorized access to research session")
        
        conversation_id = session.get("conversation_id")
        
        # Save user message about approved plan
        if conversation_id:
            try:
                user_plan_message = f"Research Plan Approved:\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(approved_plan)])
                self.add_message(
                    request,
                    db_session,
                    user_id,
                    conversation_id,
                    ConversationMessageCreateRequest(
                        role="user",
                        content=user_plan_message,
                    ),
                )
                request_logger.info("Saved approved plan as user message")
            except Exception as e:
                request_logger.error(f"Failed to save user message: {e}")
        
        # Update session with approved plan
        research_session_manager.update_approved_plan(session_id, approved_plan)
        
        # Initialize deep research agent state with approved plan
        research_state = DeepResearchAgentState(
            user_question=session["user_question"],
            memories=session.get("memories", []),
            research_plan=approved_plan,
            approved_plan=approved_plan,
            plan_approved=True,
            max_iterations=3,
        )
        
        # Execute research using astream_events directly for smooth streaming
        try:
            graph = DeepResearchAgentGraph()
            config = graph._config_graph()
            full_response = ""
            
            async for event in graph.compiled_graph.astream_events(
                input=research_state.model_dump(),
                config=config,
                version="v2",
            ):
                kind = event["event"]
                tags = event.get("tags", [])
                
                # Real-time LLM token streaming from SynthesizeNode
                if kind == "on_chat_model_stream" and Tag.streaming_node.name in tags:
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        delta = chunk.content
                        full_response += delta
                        yield self._format_sse_event("token", {"delta": delta})
                
                # Status events from all nodes (plan, search, analyze, etc.)
                elif kind == "on_custom_event":
                    event_name = event.get("name", "")
                    event_data = event.get("data", {})
                    
                    if event_name == "status":
                        msg = event_data.get("message", "")
                        if msg:
                            yield self._format_sse_event("status", {
                                "step": event_data.get("step"),
                                "message": msg,
                            })
            
            # Save result to conversation
            if conversation_id and full_response:
                full_response = self._sanitize_orphan_numeric_citations(full_response)
                try:
                    self.add_message(
                        request,
                        db_session,
                        user_id,
                        conversation_id,
                        ConversationMessageCreateRequest(
                            role="assistant",
                            content=full_response,
                        ),
                    )
                    request_logger.info("Saved deep research result to conversation")
                except Exception as e:
                    request_logger.error(f"Failed to save result to conversation: {e}")
            
            yield self._format_sse_event("done", {"output": full_response})
            
            # Cleanup session
            research_session_manager.delete_session(session_id)
            
        except Exception as e:
            request_logger.error(f"Error executing deep research: {e}")
            yield self._format_sse_event("error", {"message": str(e)})
        finally:
            if 'graph' in locals():
                del graph


conversation_service = ConversationService()
