from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.rag_agent.state import RAGAgentState, RetrievedChunk, Tag
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.rag import RAG_PROMPTS


service_logger = logger.bind(service="rag-synthesize")


class SynthesizeNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: RAGAgentState, **kwargs):
        pass

    async def ainvoke(self, state: RAGAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "rag_synthesize",
                "message": "Synthesizing answer from documents...",
            },
        )

        chunks = state.reranked_chunks if state.reranked_chunks else state.retrieved_chunks

        if not chunks:
            service_logger.warning("No chunks to synthesize")
            return {
                "context": "",
                "final_answer": RAG_PROMPTS["NO_CONTEXT_RESPONSE"],
            }

        # Build rich context from top chunks — increased from 5 to 8
        context_parts = []
        unique_files = set()
        for i, chunk in enumerate(chunks[:8]):
            chunk_obj = RetrievedChunk(**chunk) if isinstance(chunk, dict) else chunk
            
            # Build rich source header with metadata
            source_header = f"[{i+1}]"
            if chunk_obj.file_name:
                source_header = f"[{i+1}] File: {chunk_obj.file_name}"
                unique_files.add(chunk_obj.file_name)
                if chunk_obj.page_no:
                    source_header += f", Page {chunk_obj.page_no}"
            
            # Include relevance score if available
            if chunk_obj.score > 0:
                source_header += f" (relevance: {chunk_obj.score:.2f})"
            
            context_parts.append(f"{source_header}\n{chunk_obj.text}")

        context = "\n\n---\n\n".join(context_parts)

        service_logger.info(
            f"Synthesizing from {len(chunks[:8])} chunks across {len(unique_files)} files"
        )

        messages = [
            SystemMessage(content=RAG_PROMPTS["SYNTHESIZE_SYSTEM"]),
            HumanMessage(content=RAG_PROMPTS["SYNTHESIZE_USER"].format(
                user_question=state.user_question,
                context=context[:10000],  # Increased from 8K to 10K
            )),
        ]

        dispatch_custom_event(
            "status",
            {
                "step": "rag_synthesize",
                "message": f"Generating answer from {len(unique_files)} document(s)...",
            },
        )

        # Stream tokens natively using tagged config so the outer graph's
        # astream_events captures on_chat_model_stream events in real-time
        llm_with_config = azure_chat_openai_gpt_5_1.with_config(
            {"tags": [Tag.streaming_node.name]}
        )

        final_answer = ""
        async for chunk in llm_with_config.astream(messages):
            content = getattr(chunk, "content", None)
            if not content:
                continue
            final_answer += content

        service_logger.info(f"Synthesized answer of {len(final_answer)} characters from {len(unique_files)} files")

        dispatch_custom_event(
            "status",
            {
                "step": "rag_synthesize",
                "message": "Answer synthesized successfully.",
            },
        )

        return {
            "context": context,
            "final_answer": final_answer,
        }