from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, UnicodeText

from backend.databases.db import Base


class StoredFile(Base):
    __tablename__ = "FileAsset"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("User.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name = Column(UnicodeText, nullable=False)
    # Stores the blob path in Azure Blob Storage, e.g. "uploads/{user_id}/{uuid}.pdf"
    storage_path = Column(UnicodeText, nullable=False)
    mime_type = Column(UnicodeText, nullable=True, default="application/octet-stream")
    size = Column(BigInteger, nullable=False, default=0)
    ingestion_status = Column(UnicodeText, nullable=False, default="pending")
    ingestion_error = Column(UnicodeText, nullable=True, default=None)
    ingested_chunks = Column(Integer, nullable=False, default=0)
    ingested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class FileRenameRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="New file name")


class SasUrlRequest(BaseModel):
    file_ids: list[int] = Field(..., description="File IDs to generate SAS URLs for")


class FileSasResponse(BaseModel):
    sas_url: str = Field(..., description="Presigned SAS URL for file access")
    expires_at: str = Field(..., description="ISO-8601 UTC expiry of the SAS URL")


class FileResponse(BaseModel):
    id: int = Field(..., description="File ID")
    name: str = Field(..., description="Original file name")
    sas_url: Optional[str] = Field(None, description="Presigned SAS URL for file access")
    mime_type: Optional[str] = Field(None, description="MIME type")
    size: int = Field(..., description="File size in bytes")
    ingestion_status: str = Field(..., description="Ingestion status")
    ingestion_error: Optional[str] = Field(None, description="Ingestion error")
    ingested_chunks: int = Field(0, description="Number of ingested chunks")
    ingested_at: Optional[datetime] = Field(None, description="Ingested time")
    created_at: datetime = Field(..., description="Uploaded time")
    updated_at: datetime = Field(..., description="Updated time")

    model_config = ConfigDict(from_attributes=True)
