from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class DocumentSuffix(Enum):
    PDF = (".pdf",)
    DOCX = (".docx",)
    DOC = (".doc",)
    EXCEL = (".xlsx", ".xls")
    POWERPOINT = (".pptx", ".ppt")
    IMAGE = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".ico", ".webp")
    AUDIO = (".mp3", ".wav", ".ogg", ".aac", ".m4a", ".wma", ".flac")
    VIDEO = (".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm")


class IngestionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExtractedTextBlock(BaseModel):
    text: str = Field(..., description="Extracted text")
    page_no: Optional[int] = Field(None, description="Page number")
    bbox: Optional[dict[str, float]] = Field(
        None, description="Bounding box in document coordinates"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional block metadata"
    )


class IngestionChunk(BaseModel):
    chunk_index: int = Field(..., description="Chunk index in document")
    text: str = Field(..., description="Chunk text")
    page_no: Optional[int] = Field(None, description="Representative page for chunk")
    bboxes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of source bounding boxes in this chunk",
    )


class IngestionStatusResponse(BaseModel):
    file_id: int = Field(..., description="File id")
    status: str = Field(..., description="Ingestion status")
    error: Optional[str] = Field(None, description="Error details")
    chunks: int = Field(0, description="Number of ingested chunks")
    ingested_at: Optional[datetime] = Field(None, description="Ingested timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last status update")


class IngestionRunRequest(BaseModel):
    file_ids: list[int] = Field(
        ...,
        min_length=1,
        description="File ids to ingest",
    )


class IngestionRunResponse(BaseModel):
    file_id: int = Field(..., description="File id")
    status: str = Field(..., description="Ingestion status after run")
    chunks: int = Field(0, description="Ingested chunk count")
    error: Optional[str] = Field(None, description="Error details")
