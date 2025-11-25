from pydantic import BaseModel
from typing import List, Dict, Any, BinaryIO, Optional


# ===== Retriver Input and Output ======
class RetrieverModel(BaseModel):
    query: str
    collection_name: str
    kb_ids: List[str]
    domain: Optional[str] = None
    limit: int = 3


class RetrieverModelResponse(BaseModel):
    results: List[Dict[str, Any]]
    

# ===== S3 Service Upload File with Path Input and Output ======
class S3ServiceUploadFileWithFilePathModel(BaseModel):
    key: str
    file_path: str

# ===== S3 Service Get Presigned URL Input and Output ======
class S3ServiceGetPresignedURLModel(BaseModel):
    key: str
    expiration: int = 7 * 24 * 3600

class S3ServiceGetPresignedURLModelResponse(BaseModel):
    url: str


# ===== S3 Service Upload File with Binary Input and Output ======
class S3ServiceUploadFileWithBinaryModel(BaseModel):
    key: str
    file: bytes
    
# ===== S3 Service Delete File with Path Input and Output ======
class S3ServiceDeleteFileModel(BaseModel):
    key: str


class MessageModelResponse(BaseModel):
    message: str
    success: bool