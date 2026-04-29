from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, UnicodeText

from backend.databases.db import Base


class AgentSkill(Base):
    """Stores user-uploaded agent skills (Claude Code SKILL.md format)."""
    __tablename__ = "AgentSkill"
    __table_args__ = (
        Index(
            "ix_AgentSkill_user_selected_active_deleted",
            "user_id",
            "is_selected",
            "is_active",
            "deleted_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("User.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name = Column(UnicodeText, nullable=False)
    description = Column(UnicodeText, nullable=True)
    storage_path = Column(UnicodeText, nullable=False)
    blob_path = Column(UnicodeText, nullable=True)  # Azure Blob Storage path for download
    skill_content = Column(UnicodeText, nullable=True)
    allowed_tools = Column(UnicodeText, nullable=True)
    file_type = Column(UnicodeText, nullable=False, default="md")
    is_active = Column(Boolean, nullable=False, default=True)
    is_selected = Column(Boolean, nullable=False, default=True)
    size = Column(BigInteger, nullable=False, default=0)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    purge_after = Column(DateTime(timezone=True), nullable=True)
    purged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


# Pydantic Models for API

class SkillCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Skill name")
    description: Optional[str] = Field(None, description="Skill description")
    allowed_tools: Optional[str] = Field(None, description="Space-separated allowed tools")
    is_selected: bool = Field(True, description="Whether skill is selected for use")


class SkillUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    allowed_tools: Optional[str] = None
    is_active: Optional[bool] = None
    is_selected: Optional[bool] = None


class SkillResponse(BaseModel):
    id: int = Field(..., description="Skill ID")
    user_id: int = Field(..., description="User ID")
    name: str = Field(..., description="Skill name")
    description: Optional[str] = Field(None, description="Skill description")
    storage_path: str = Field(..., description="Storage path on server")
    allowed_tools: Optional[str] = Field(None, description="Allowed tools")
    file_type: str = Field(..., description="File type: md or zip")
    is_active: bool = Field(..., description="Whether skill is active")
    is_selected: bool = Field(..., description="Whether skill is selected")
    size: int = Field(..., description="File size in bytes")
    download_url: Optional[str] = Field(None, description="Temporary SAS download URL")
    created_at: datetime = Field(..., description="Created time")
    updated_at: datetime = Field(..., description="Updated time")

    model_config = ConfigDict(from_attributes=True)


class SandboxResponse(BaseModel):
    id: int = Field(..., description="Sandbox session ID")
    sandbox_index: int = Field(..., description="Sandbox index (0-9)")
    status: str = Field(..., description="Sandbox status: ready, busy, error")
    current_skill_id: Optional[int] = Field(None, description="Currently executing skill ID")
    task_description: Optional[str] = Field(None, description="Current task description")
    progress: int = Field(..., description="Progress percentage (0-100)")
    started_at: Optional[datetime] = Field(None, description="When task started")
    completed_at: Optional[datetime] = Field(None, description="When task completed")

    model_config = ConfigDict(from_attributes=True)


class SkillExecutionRequest(BaseModel):
    skill_ids: List[int] = Field(default_factory=list, description="Skill IDs to use (empty = all selected)")
    user_message: str = Field(..., min_length=1, description="User message/task for skills")
    conversation_id: int = Field(..., description="Conversation ID")


class SkillSelectRequest(BaseModel):
    skill_id: int = Field(..., description="Skill ID to toggle selection")
    is_selected: bool = Field(..., description="New selection state")


class SandboxStatusUpdate(BaseModel):
    sandbox_index: int = Field(..., description="Sandbox index (0-9)")
    status: str = Field(..., description="New status")
    progress: Optional[int] = Field(None, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")


class SandboxSocketEvent(BaseModel):
    id: int = Field(..., description="Sandbox session ID")
    user_id: Optional[int] = Field(None, description="Current owner user id")
    sandbox_index: int = Field(..., description="Sandbox index (0-9)")
    status: str = Field(..., description="Sandbox status")
    current_skill_id: Optional[int] = Field(None, description="Current skill id")
    task_description: Optional[str] = Field(None, description="Current task description")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
