from typing import Optional

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
)
from backend.api.files.model import StoredFile
from backend.databases.db import get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.utils.constants import Message

service_logger = logger.bind(service="conversation-service")


class ConversationService:
    @staticmethod
    def _get_request_logger(request: Request | None = None, user_id: int | None = None):
        return service_logger.bind(
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
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
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
            .filter(Conversation.user_id == user_id)
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
        db_session.delete(conversation)
        db_session.commit()
        request_logger.info("Deleted conversation")
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

        if not files_request.file_ids:
            conversation.files = []
            conversation.updated_at = get_utc_now()
            db_session.commit()
            db_session.refresh(conversation)
            request_logger.info("Detached all files from conversation")
            return self._get_user_conversation(
                db_session, user_id, conversation_id, request_logger
            )

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


conversation_service = ConversationService()
