from pydantic import BaseModel, Field

class MigrationS3Request(BaseModel):
    source_bucket: str = Field(..., description="Source bucket name")
    target_bucket: str = Field(..., description="Target bucket name")
    prefix: str = Field(..., description="Prefix of the objects to migrate")
    
class MessageResponse(BaseModel):
    status_code: int = Field(..., description="Status code")
    message: str = Field(..., description="Message")