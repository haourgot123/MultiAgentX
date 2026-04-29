from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    UnicodeText,
)

from backend.config.settings import _settings
from backend.databases.db import Base


VideoAspectRatio = Literal["16:9", "9:16", "1:1"]
VideoStyle = Literal[
    "cinematic",
    "educational",
    "product_demo",
    "social_short",
    "slideshow",
]
VideoStatus = Literal[
    "queued",
    "researching",
    "storyboarding",
    "rendering",
    "completed",
    "failed",
]


class VideoGenerationJob(Base):
    __tablename__ = "VideoGenerationJob"
    __table_args__ = (
        Index(
            "ix_VideoGenerationJob_user_deleted_created",
            "user_id",
            "deleted_at",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("User.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title = Column(UnicodeText, nullable=True)
    prompt = Column(UnicodeText, nullable=False)
    style = Column(UnicodeText, nullable=False)
    aspect_ratio = Column(UnicodeText, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    fps = Column(Integer, nullable=False)
    web_search_enabled = Column(Boolean, nullable=False, default=True)
    status = Column(UnicodeText, index=True, nullable=False, default="queued")
    progress = Column(Integer, nullable=False, default=0)
    storyboard_json = Column(JSON, nullable=True)
    sources_json = Column(JSON, nullable=True)
    video_blob_path = Column(UnicodeText, nullable=True)
    thumbnail_blob_path = Column(UnicodeText, nullable=True)
    error_message = Column(UnicodeText, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    purge_after = Column(DateTime(timezone=True), nullable=True)
    purged_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class VideoGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Video prompt")
    duration_seconds: int = Field(
        default=_settings.video_generation.default_duration_seconds,
        ge=5,
        le=_settings.video_generation.max_duration_seconds,
    )
    fps: Literal[24, 30] = Field(default=_settings.video_generation.default_fps)
    aspect_ratio: VideoAspectRatio = Field(default="16:9")
    style: VideoStyle = Field(default="educational")
    web_search_enabled: bool = Field(default=True)

    @field_validator("prompt")
    @classmethod
    def normalize_prompt(cls, value: str) -> str:
        prompt = value.strip()
        if not prompt:
            raise ValueError("Prompt is required")
        return prompt


class VideoGenerationUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Video title")

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Title is required")
        return title[:255]


class VideoGenerationJobResponse(BaseModel):
    id: int = Field(..., description="Video generation job ID")
    title: str
    prompt: str
    style: str
    aspect_ratio: str
    duration_seconds: int
    fps: int
    web_search_enabled: bool
    status: str
    progress: int
    storyboard: Optional[dict[str, Any] | list[Any]] = None
    sources: Optional[list[dict[str, Any]]] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
