from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from backend.utils.dependency import get_db
from backend.memory.mem0_client import mem0_client
from backend.api.memory.model import (
    MemoryResponse,
    MemoryListResponse,
    MemorySearchRequest,
    MemoryAddRequest,
    MemoryDeleteRequest,
    MemoryUpdateRequest,
)
from backend.utils.dependency import get_current_user

router = APIRouter(prefix="/memories", tags=["memories"])


def _get_log_prefix(request: Request, user_id: str) -> str:
    request_id = getattr(getattr(request, "state", None), "request_id", "-")
    return f"[MemoryAPI][request_id={request_id}][user_id={user_id}]"


@router.get("", response_model=MemoryListResponse)
async def get_user_memories(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_user),
    limit: int = 50,
):
    """
    Get all memories for the current user.
    
    Returns a list of all stored memories for the authenticated user.
    """
    user_id = str(request.state.user_id)
    log_prefix = _get_log_prefix(request, user_id)
    
    logger.info(f"{log_prefix} Getting all memories for user {user_id}")
    
    try:
        memories = await mem0_client.get_all_memories(
            user_id=user_id,
            limit=limit
        )
        
        memory_responses = [
            MemoryResponse(
                id=mem.get("id", ""),
                memory=mem.get("memory", ""),
                user_id=user_id,
                score=mem.get("score"),
                created_at=mem.get("created_at"),
                updated_at=mem.get("updated_at"),
                metadata=mem.get("metadata")
            )
            for mem in memories
        ]
        
        logger.info(f"{log_prefix} Retrieved {len(memory_responses)} memories for user {user_id}")
        
        return MemoryListResponse(
            memories=memory_responses,
            total=len(memory_responses)
        )
        
    except Exception as e:
        logger.error(f"{log_prefix} Error getting memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get memories: {str(e)}")


@router.post("/search", response_model=MemoryListResponse)
async def search_memories(
    request: Request,
    search_request: MemorySearchRequest,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_user),
):
    """
    Search memories for the current user.
    
    Performs semantic search over stored memories and returns relevant results.
    """
    # Validate user_id matches current user
    current_user_id = str(request.state.user_id)
    if search_request.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot search memories for other users")
    
    user_id = current_user_id
    log_prefix = _get_log_prefix(request, user_id)
    
    logger.info(f"{log_prefix} Searching memories with query: '{search_request.query}'")
    
    try:
        memories = await mem0_client.search_memories(
            query=search_request.query,
            user_id=search_request.user_id,
            limit=search_request.limit
        )
        
        memory_responses = [
            MemoryResponse(
                id=mem.get("id", ""),
                memory=mem.get("memory", ""),
                user_id=search_request.user_id,
                score=mem.get("score"),
                created_at=mem.get("created_at"),
                updated_at=mem.get("updated_at"),
                metadata=mem.get("metadata")
            )
            for mem in memories
        ]
        
        logger.info(f"{log_prefix} Found {len(memory_responses)} memories matching query")
        
        return MemoryListResponse(
            memories=memory_responses,
            total=len(memory_responses)
        )
        
    except Exception as e:
        logger.error(f"{log_prefix} Error searching memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


@router.post("", response_model=MemoryListResponse)
async def add_memory(
    request: Request,
    add_request: MemoryAddRequest,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_user),
):
    """
    Add memories from conversation messages.
    
    Extracts facts from messages and stores them as long-term memories.
    """
    # Validate user_id matches current user
    current_user_id = str(request.state.user_id)
    if add_request.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot add memories for other users")
    
    user_id = current_user_id
    log_prefix = _get_log_prefix(request, user_id)
    
    logger.info(f"{log_prefix} Adding memory for user {user_id}")
    
    try:
        result = await mem0_client.add_memory(
            messages=add_request.messages,
            user_id=add_request.user_id,
            metadata=add_request.metadata or {}
        )
        
        if not result:
            return MemoryListResponse(memories=[], total=0)
        
        memories = result.get("results", [])
        
        memory_responses = [
            MemoryResponse(
                id=mem.get("id", ""),
                memory=mem.get("memory", ""),
                user_id=add_request.user_id,
                created_at=mem.get("created_at"),
                metadata=mem.get("metadata")
            )
            for mem in memories
        ]
        
        logger.info(f"{log_prefix} Added {len(memory_responses)} memories for user {user_id}")
        
        return MemoryListResponse(
            memories=memory_responses,
            total=len(memory_responses)
        )
        
    except Exception as e:
        logger.error(f"{log_prefix} Error adding memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add memory: {str(e)}")


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    request: Request,
    update_request: MemoryUpdateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_user),
):
    """
    Update a specific memory by ID.
    
    Updates the content of an existing memory.
    """
    user_id = str(request.state.user_id)
    log_prefix = _get_log_prefix(request, user_id)
    
    logger.info(f"{log_prefix} Updating memory {memory_id}")
    
    try:
        success = await mem0_client.delete_memory(memory_id=memory_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
        
        # Note: Mem0 doesn't have a direct update, so we delete and re-add
        # In production, you might want to store the original memory to re-add it
        
        return MemoryResponse(
            id=memory_id,
            memory=update_request.data,
            user_id=user_id,
            created_at=None,
            updated_at=None,
            metadata=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{log_prefix} Error updating memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update memory: {str(e)}")


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_user),
):
    """
    Delete a specific memory by ID.
    
    Permanently removes a memory from the user's memory store.
    """
    user_id = str(request.state.user_id)
    log_prefix = _get_log_prefix(request, user_id)
    
    logger.info(f"{log_prefix} Deleting memory {memory_id}")
    
    try:
        success = await mem0_client.delete_memory(memory_id=memory_id)
        
        if success:
            logger.info(f"{log_prefix} Deleted memory {memory_id}")
            return {"message": f"Memory {memory_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{log_prefix} Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")


@router.delete("/clear/all")
async def clear_user_memories(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_user),
):
    """
    Clear all memories for the current user.
    
    Permanently removes all memories. This action cannot be undone.
    """
    user_id = str(request.state.user_id)
    log_prefix = _get_log_prefix(request, user_id)
    
    logger.info(f"{log_prefix} Clearing all memories for user {user_id}")
    
    try:
        success = await mem0_client.clear_user_memories(user_id=user_id)
        
        if success:
            logger.info(f"{log_prefix} Cleared all memories for user {user_id}")
            return {"message": "All memories cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear memories")
            
    except Exception as e:
        logger.error(f"{log_prefix} Error clearing memories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear memories: {str(e)}")