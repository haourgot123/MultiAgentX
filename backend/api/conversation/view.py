from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.requests import Request
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

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
)
from backend.api.conversation.service import conversation_service
from backend.utils.dependency import get_current_user, get_db

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
    dependencies=[Depends(get_current_user)],
)


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


@router.get("", response_model=list[ConversationResponse], status_code=status.HTTP_200_OK)
def list_conversations(
    request: Request,
    chat_type: Optional[str] = None,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    conversations = conversation_service.list_conversations(db_session, user_id, chat_type)
    return [_to_conversation_response(conversation) for conversation in conversations]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    request: Request,
    create_request: ConversationCreateRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    conversation = conversation_service.create_conversation(
        db_session, user_id, create_request
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
    conversation = conversation_service.get_conversation(db_session, user_id, conversation_id)
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
        db_session, user_id, conversation_id, rename_request
    )
    return _to_conversation_response(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    request: Request,
    conversation_id: int,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    response = conversation_service.delete_conversation(db_session, user_id, conversation_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@router.put(
    "/{conversation_id}/files",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
def update_conversation_files(
    request: Request,
    conversation_id: int,
    files_request: ConversationFilesUpdateRequest,
    db_session: Session = Depends(get_db),
):
    user_id = request.state.user_id
    conversation = conversation_service.update_conversation_files(
        db_session, user_id, conversation_id, files_request
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
        db_session, user_id, conversation_id, message_request
    )
    return ConversationMessageCreateResponse(
        message=_to_message_response(message),
        conversation=_to_conversation_response(conversation),
    )
