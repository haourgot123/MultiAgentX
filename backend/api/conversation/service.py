from typing import Optional

from sqlalchemy.orm import Session, selectinload

from backend.api.conversation.model import (
    Conversation,
    ConversationCreateRequest,
    ConversationFilesUpdateRequest,
    ConversationMessage,
    ConversationMessageCreateRequest,
    ConversationRenameRequest,
)
from backend.api.files.model import StoredFile
from backend.databases.db import get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.utils.constants import Message


class ConversationService:
    @staticmethod
    def _normalize_title(title: Optional[str]) -> str:
        if not title or not title.strip():
            return "New Chat"
        return title.strip()[:255]

    @staticmethod
    def _build_file_chat_title(conversation: Conversation, message_content: str) -> str:
        if conversation.files:
            first_file_name = conversation.files[0].name.strip() or "File"
            if len(conversation.files) > 1:
                file_prefix = f"{first_file_name} +{len(conversation.files) - 1}"
            else:
                file_prefix = first_file_name
        else:
            file_prefix = "File Chat"

        trimmed_message = message_content.strip()
        message_snippet = (
            trimmed_message[:40] + "..." if len(trimmed_message) > 40 else trimmed_message
        )
        title = f"{file_prefix} - {message_snippet}" if message_snippet else file_prefix
        return title[:255]

    def _get_user_conversation(
        self, db_session: Session, user_id: int, conversation_id: int
    ) -> Conversation:
        conversation = (
            db_session.query(Conversation)
            .options(
                selectinload(Conversation.files),
                selectinload(Conversation.messages),
            )
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )
        if not conversation:
            raise ObjectNotFoundException(message=Message.MESSAGE_CONVERSATION_NOT_FOUND)
        return conversation

    def list_conversations(
        self, db_session: Session, user_id: int, chat_type: Optional[str] = None
    ) -> list[Conversation]:
        query = (
            db_session.query(Conversation)
            .options(
                selectinload(Conversation.files),
                selectinload(Conversation.messages),
            )
            .filter(Conversation.user_id == user_id)
        )
        if chat_type:
            query = query.filter(Conversation.chat_type == chat_type)

        return query.order_by(Conversation.updated_at.desc()).all()

    def create_conversation(
        self,
        db_session: Session,
        user_id: int,
        create_request: ConversationCreateRequest,
    ) -> Conversation:
        now = get_utc_now()
        conversation = Conversation(
            user_id=user_id,
            title=self._normalize_title(create_request.title),
            chat_type=create_request.chat_type,
            created_at=now,
            updated_at=now,
        )

        if create_request.file_ids:
            files = (
                db_session.query(StoredFile)
                .filter(
                    StoredFile.user_id == user_id, StoredFile.id.in_(create_request.file_ids)
                )
                .all()
            )
            if len(files) != len(set(create_request.file_ids)):
                raise InvalidRequestException(message=Message.MESSAGE_FILE_NOT_FOUND)
            conversation.files = files

        db_session.add(conversation)
        db_session.commit()
        db_session.refresh(conversation)

        return self._get_user_conversation(db_session, user_id, conversation.id)

    def get_conversation(
        self, db_session: Session, user_id: int, conversation_id: int
    ) -> Conversation:
        return self._get_user_conversation(db_session, user_id, conversation_id)

    def rename_conversation(
        self,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        rename_request: ConversationRenameRequest,
    ) -> Conversation:
        conversation = self._get_user_conversation(db_session, user_id, conversation_id)
        conversation.title = self._normalize_title(rename_request.title)
        conversation.updated_at = get_utc_now()
        db_session.commit()
        db_session.refresh(conversation)
        return self._get_user_conversation(db_session, user_id, conversation_id)

    def delete_conversation(
        self, db_session: Session, user_id: int, conversation_id: int
    ) -> dict:
        conversation = self._get_user_conversation(db_session, user_id, conversation_id)
        db_session.delete(conversation)
        db_session.commit()
        return {"message": Message.MESSAGE_CONVERSATION_DELETED_SUCCESSFULLY}

    def update_conversation_files(
        self,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        files_request: ConversationFilesUpdateRequest,
    ) -> Conversation:
        conversation = self._get_user_conversation(db_session, user_id, conversation_id)
        if conversation.chat_type != "file":
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_REQUEST)

        if not files_request.file_ids:
            conversation.files = []
            conversation.updated_at = get_utc_now()
            db_session.commit()
            db_session.refresh(conversation)
            return self._get_user_conversation(db_session, user_id, conversation_id)

        files = (
            db_session.query(StoredFile)
            .filter(StoredFile.user_id == user_id, StoredFile.id.in_(files_request.file_ids))
            .all()
        )
        if len(files) != len(set(files_request.file_ids)):
            raise InvalidRequestException(message=Message.MESSAGE_FILE_NOT_FOUND)

        conversation.files = files
        conversation.updated_at = get_utc_now()
        db_session.commit()
        db_session.refresh(conversation)
        return self._get_user_conversation(db_session, user_id, conversation_id)

    def add_message(
        self,
        db_session: Session,
        user_id: int,
        conversation_id: int,
        message_request: ConversationMessageCreateRequest,
    ) -> tuple[ConversationMessage, Conversation]:
        conversation = self._get_user_conversation(db_session, user_id, conversation_id)
        existing_message_count = len(conversation.messages)
        now = get_utc_now()

        message = ConversationMessage(
            conversation_id=conversation.id,
            role=message_request.role,
            content=message_request.content.strip(),
            created_at=now,
            updated_at=now,
        )
        db_session.add(message)

        if existing_message_count == 0 and message_request.role == "user":
            if conversation.chat_type == "file":
                conversation.title = self._build_file_chat_title(
                    conversation, message_request.content
                )
            elif conversation.title == "New Chat":
                trimmed_title = message_request.content.strip()[:50]
                conversation.title = (
                    trimmed_title + "..."
                    if len(message_request.content.strip()) > 50
                    else trimmed_title
                )

        conversation.updated_at = now

        db_session.commit()
        db_session.refresh(message)
        updated_conversation = self._get_user_conversation(
            db_session, user_id, conversation_id
        )
        return message, updated_conversation


conversation_service = ConversationService()
