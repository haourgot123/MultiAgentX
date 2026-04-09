from datetime import datetime
from typing import Literal, Optional, List

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, UnicodeText
from sqlalchemy.orm import relationship

from backend.databases.db import Base

conversation_files = Table(
    "Conversation_File",
    Base.metadata,
    Column(
        "conversation_id",
        Integer,
        ForeignKey("Conversation.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "file_id",
        Integer,
        ForeignKey("FileAsset.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Conversation(Base):
    __tablename__ = "Conversation"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("User.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title = Column(UnicodeText, nullable=False, default="New Chat")
    chat_type = Column(UnicodeText, nullable=False, default="normal")
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    files = relationship("StoredFile", secondary=conversation_files)


class ConversationMessage(Base):
    __tablename__ = "ConversationMessage"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey("Conversation.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role = Column(UnicodeText, nullable=False)
    content = Column(UnicodeText, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    conversation = relationship("Conversation", back_populates="messages")


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Conversation title")
    chat_type: Literal["normal", "file"] = Field(
        "normal", description="Conversation type"
    )
    file_ids: list[int] = Field(
        default_factory=list, description="File IDs attached to this conversation"
    )


class ConversationRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Conversation title")


class ConversationFilesUpdateRequest(BaseModel):
    file_ids: list[int] = Field(
        default_factory=list,
        description="Attached file IDs for this conversation",
    )


class ConversationMessageCreateRequest(BaseModel):
    role: Literal["user", "assistant"] = Field(..., description="Message role")
    content: str = Field(..., min_length=1, description="Message content")


class ConversationMessageResponse(BaseModel):
    id: int = Field(..., description="Message ID")
    role: Literal["user", "assistant"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Created time")
    updated_at: datetime = Field(..., description="Updated time")

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: int = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    chat_type: Literal["normal", "file"] = Field(..., description="Conversation type")
    file_ids: list[int] = Field(default_factory=list, description="Attached file IDs")
    message_count: int = Field(0, description="Number of messages")
    created_at: datetime = Field(..., description="Created time")
    updated_at: datetime = Field(..., description="Updated time")

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    messages: list[ConversationMessageResponse] = Field(
        default_factory=list, description="Conversation messages"
    )


class ConversationMessageCreateResponse(BaseModel):
    message: ConversationMessageResponse = Field(..., description="Created message")
    conversation: ConversationResponse = Field(
        ..., description="Updated conversation snapshot"
    )


class ChatRequest(BaseModel):
    chat_type: Literal["normal", "file"] = Field(..., description="Chat type")
    conversation_id: int = Field(..., description="Conversation ID")
    user_question: str = Field(..., description="User question")
    is_web_search_enabled: Optional[bool] = Field(False, description="Is web search enabled")
    is_deep_research_enabled: Optional[bool] = Field(False, description="Is deep research enabled")
    is_generate_image_enabled: Optional[bool] = Field(False, description="Is generate image enabled")
    is_rag_enabled: Optional[bool] = Field(False, description="Is RAG enabled")
    file_ids: Optional[List[int]] = Field(default_factory=list, description="File IDs for RAG")
    approved_research_plan: Optional[List[str]] = Field(None, description="Approved research plan for deep research (optional)")
    deep_research_session_id: Optional[str] = Field(None, description="Deep research session ID for resuming (optional)")


class DeepResearchPlanRequest(BaseModel):
    conversation_id: int = Field(..., description="Conversation ID")
    user_question: str = Field(..., description="User question for deep research")


class DeepResearchApproveRequest(BaseModel):
    session_id: str = Field(..., description="Research session ID")
    approved_plan: List[str] = Field(..., description="Approved research plan sub-questions")


class DeepResearchPlanResponse(BaseModel):
    session_id: str = Field(..., description="Research session ID")
    plan: List[str] = Field(..., description="Generated research plan sub-questions")
    message: str = Field(..., description="Status message")
