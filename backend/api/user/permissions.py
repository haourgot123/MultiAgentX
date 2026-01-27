"""Helper utilities for role-based access control."""

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.utils.constants import Message, RoleType


def check_admin_role(request: Request, db_session: Session) -> None:
    """Check if the current user has admin role.
    
    Args:
        request: FastAPI request object containing user state.
        db_session: Database session for querying user roles.
        
    Raises:
        HTTPException: If user doesn't have admin role (403 Forbidden).
    """
    from backend.api.user.service import user_service
    
    roles = user_service.get_user_roles_by_id(db_session, request.state.user_id)
    role_ids = [role.id for role in roles]
    admin_role_id = RoleType.ADMIN.value
    
    logger.debug(f"User {request.state.user_id} role IDs: {role_ids}")
    
    if admin_role_id not in role_ids:
        logger.warning(
            f"User {request.state.user_id} attempted admin action without admin role"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )


def check_user_permission(request: Request, target_user_id: int) -> None:
    """Check if the current user can access target user's resources.
    
    Users can only access their own resources unless they are admin.
    
    Args:
        request: FastAPI request object containing user state.
        target_user_id: ID of the user being accessed.
        
    Raises:
        HTTPException: If user doesn't have permission (401 Unauthorized).
    """
    if target_user_id != request.state.user_id:
        logger.warning(
            f"User {request.state.user_id} attempted to access user {target_user_id}'s resources"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )
