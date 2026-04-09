from typing import List, Optional
from pydantic import BaseModel, Field


class MemoryResponse(BaseModel):
    """Response model for a single memory."""
    
    id: str = Field(..., description="Memory ID")
    memory: str = Field(..., description="Memory content (extracted fact)")
    user_id: str = Field(..., description="User ID")
    score: Optional[float] = Field(None, description="Relevance score (for search results)")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    metadata: Optional[dict] = Field(None, description="Memory metadata")
    
    model_config = {"from_attributes": True}


class MemoryListResponse(BaseModel):
    """Response model for list of memories."""
    
    memories: List[MemoryResponse] = Field(default_factory=list, description="List of memories")
    total: int = Field(..., description="Total number of memories")


class MemorySearchRequest(BaseModel):
    """Request model for searching memories."""
    
    query: str = Field(..., description="Search query", min_length=1)
    user_id: str = Field(..., description="User ID")
    limit: int = Field(10, description="Maximum number of results", ge=1, le=50)


class MemoryAddRequest(BaseModel):
    """Request model for adding memories manually."""
    
    messages: List[dict] = Field(..., description="Conversation messages", min_items=1)
    user_id: str = Field(..., description="User ID")
    metadata: Optional[dict] = Field(None, description="Optional metadata")
    infer: bool = Field(True, description="Auto-extract facts from messages")


class MemoryDeleteRequest(BaseModel):
    """Request model for deleting memories."""
    
    user_id: str = Field(..., description="User ID")
    memory_id: Optional[str] = Field(None, description="Specific memory ID to delete")


class MemoryUpdateRequest(BaseModel):
    """Request model for updating a memory."""
    
    memory_id: str = Field(..., description="Memory ID to update")
    data: str = Field(..., description="New memory content", min_length=1)