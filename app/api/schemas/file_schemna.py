from pydantic import BaseModel, Field
from typing import List, Literal
from enum import Enum
from app.config.settings import _settings


class CollectionName(str, Enum):
    DEFAULT = _settings.qdrant.default_collection
    COMPANY = _settings.qdrant.company_collection
    PROJECT = _settings.qdrant.project_collection

class FileSchema(BaseModel):
    file_name: str = Field(..., description="The name of the file")
    file_id: str = Field(..., description="The ID of the file")
    file_url: str = Field(..., description="The URL of the file")
    file_size: float = Field(..., description="Size of file (MB)")


class UploadFileRequest(BaseModel):
    files: List[FileSchema] = Field(..., description="The files to upload")
    
class UploadFileResponse(BaseModel):
    task_id: str = Field(..., description="The ID of the task")
    message: str = Field(..., description="The message of the response")

class MessageResponse(BaseModel):
    status: Literal["success", "failed"] = Field(..., description="The status of the response")
    message: str = Field(..., description="The message of the response")