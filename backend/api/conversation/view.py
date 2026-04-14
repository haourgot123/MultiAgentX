from typing import Optional
from loguru import logger
from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.requests import Request
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from fastapi.responses import StreamingResponse
from backend.api.conversation.model import (
    Conversation,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationFilesUpdateRequest,
    ConversationMessage,
    ConversationMessageCreateRequest,
    ConversationMessageCreateResponse,
    ConversationMessageResponse,
    ConversationRenameRequest,
    ConversationResponse,
    ChatRequest,
    DeepResearchPlanRequest,
    DeepResearchApproveRequest,
    DeepResearchPlanResponse,
    RetrievalRecord,
    RetrievalRecordResponse,
)
from backend.api.conversation.service import conversation_service
from backend.api.data_ingestion.model import IngestionStatus
from backend.api.data_ingestion.service import data_ingestion_service
from backend.api.files.model import StoredFile
from backend.exceptions.model import InvalidRequestException
from backend.utils.constants import Message
from backend.utils.dependency import get_current_user, get_db

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
    dependencies=[Depends(get_current_user)],
)

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _to_conversation_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        chat_type=conversation.chat_type,
        file_ids=[file.id for file in conversation.files],
        message_count=len(conversation.messages),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _to_message_response(message: ConversationMessage) -> ConversationMessageResponse:
    return ConversationMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def _enqueue_ingestion_for_conversation_files(
    background_tasks: BackgroundTasks,
    request: Request,
    *,
    user_id: int,
    files: list[StoredFile],
) -> None:
    candidate_ids = {
        file.id
        for file in files
        if (file.ingestion_status or "").lower()
        in {IngestionStatus.PENDING.value, IngestionStatus.FAILED.value}
    }
    for file_id in candidate_ids:
        data_ingestion_service.emit_queued_status(
            user_id=user_id,
            file_id=file_id,
            request=request,
        )
        background_tasks.add_task(data_ingestion_service.ingest_file_by_id, user_id, file_id)


@router.get("", response_model=list[ConversationResponse], status_code=status.HTTP_200_OK)
def list_conversations(
    request: Request,
    chat_type: Optional[str] = None,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    conversations = conversation_service.list_conversations(
        request, db_session, user_id, chat_type
    )
    return [_to_conversation_response(conversation) for conversation in conversations]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    request: Request,
    background_tasks: BackgroundTasks,
    create_request: ConversationCreateRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    conversation = conversation_service.create_conversation(
        request, db_session, user_id, create_request
    )
    if conversation.chat_type == "file" and conversation.files:
        _enqueue_ingestion_for_conversation_files(
            background_tasks,
            request,
            user_id=user_id,
            files=conversation.files,
        )
    return _to_conversation_response(conversation)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
)
def get_conversation(
    request: Request,
    conversation_id: int,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    conversation = conversation_service.get_conversation(
        request, db_session, user_id, conversation_id
    )
    return ConversationDetailResponse(
        **_to_conversation_response(conversation).model_dump(),
        messages=[_to_message_response(message) for message in conversation.messages],
    )


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
def rename_conversation(
    request: Request,
    conversation_id: int,
    rename_request: ConversationRenameRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    conversation = conversation_service.rename_conversation(
        request, db_session, user_id, conversation_id, rename_request
    )
    return _to_conversation_response(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    request: Request,
    conversation_id: int,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    response = conversation_service.delete_conversation(
        request, db_session, user_id, conversation_id
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@router.put(
    "/{conversation_id}/files",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
def update_conversation_files(
    request: Request,
    conversation_id: int,
    background_tasks: BackgroundTasks,
    files_request: ConversationFilesUpdateRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    conversation = conversation_service.update_conversation_files(
        request, db_session, user_id, conversation_id, files_request
    )
    if conversation.chat_type == "file" and conversation.files:
        _enqueue_ingestion_for_conversation_files(
            background_tasks,
            request,
            user_id=user_id,
            files=conversation.files,
        )
    return _to_conversation_response(conversation)


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationMessageCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    request: Request,
    conversation_id: int,
    message_request: ConversationMessageCreateRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    message, conversation = conversation_service.add_message(
        request, db_session, user_id, conversation_id, message_request
    )
    return ConversationMessageCreateResponse(
        message=_to_message_response(message),
        conversation=_to_conversation_response(conversation),
    )


@router.post(
    "/chat",
    status_code=status.HTTP_201_CREATED,
)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    db_session: Session = Depends(get_db),
):
    logger.info(f"Chat request: {chat_request}")
    if chat_request.chat_type == "normal":
        # Streaming response
        return StreamingResponse(
            conversation_service.normal_chat(
                request, 
                db_session, 
                request.state.user_id, 
                chat_request.conversation_id, 
                chat_request.user_question,
                chat_request.is_web_search_enabled,
                chat_request.is_deep_research_enabled,
                chat_request.is_generate_image_enabled
            ),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
            status_code=status.HTTP_201_CREATED,
        )
    elif chat_request.chat_type == "file":
        return StreamingResponse(
            conversation_service.file_chat(
                request, 
                db_session, 
                request.state.user_id, 
                chat_request.conversation_id,
                chat_request.user_question,
            ),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
            status_code=status.HTTP_201_CREATED,
        )
    else:
        raise InvalidRequestException(message = Message.MESSAGE_INVALID_REQUEST)


@router.post(
    "/deep-research/plan",
    response_model=DeepResearchPlanResponse,
    status_code=status.HTTP_200_OK,
)
async def create_deep_research_plan(
    request: Request,
    plan_request: DeepResearchPlanRequest,
    db_session: Session = Depends(get_db),
):
    logger.info(f"Deep research plan request: {plan_request}")
    result = await conversation_service.create_deep_research_plan(
        request,
        db_session,
        request.state.user_id,
        plan_request.conversation_id,
        plan_request.user_question,
    )
    return result


@router.post(
    "/deep-research/approve",
    status_code=status.HTTP_201_CREATED,
)
async def approve_deep_research_plan(
    request: Request,
    approve_request: DeepResearchApproveRequest,
    db_session: Session = Depends(get_db),
):
    logger.info(f"Deep research approve request: {approve_request}")
    return StreamingResponse(
        conversation_service.approve_deep_research_plan(
            request,
            db_session,
            request.state.user_id,
            approve_request.session_id,
            approve_request.approved_plan,
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/{conversation_id}/messages/{message_id}/retrievals",
    response_model=list[RetrievalRecordResponse],
    status_code=status.HTTP_200_OK,
)
def get_message_retrievals(
    request: Request,
    conversation_id: int,
    message_id: int,
    db_session: Session = Depends(get_db),
):
    """Get retrieval records for a specific message (bbox data for PDF highlighting)."""
    user_id = request.state.user_id
    records = (
        db_session.query(RetrievalRecord)
        .filter(
            RetrievalRecord.conversation_id == conversation_id,
            RetrievalRecord.message_id == message_id,
            RetrievalRecord.user_id == user_id,
        )
        .order_by(RetrievalRecord.citation_label)
        .all()
    )
    return [RetrievalRecordResponse.model_validate(r) for r in records]
