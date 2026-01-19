from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.orm import Session

from backend.api.user.model import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    SelfUserInformationUpdateRequest,
    SelfUserInformationUpdateResponse,
    UserResponse,
    UserUpdateRequest,
)
from backend.api.user.service import user_service
from backend.utils.constants import Message, RoleType
from backend.utils.dependency import get_current_user, get_db

router = APIRouter(
    prefix="/user", tags=["User"], dependencies=[Depends(get_current_user)]
)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    description="Logout a user",
)
async def logout(request: Request, user_id: int, db_session: Session = Depends(get_db)):
    if user_id != request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )
    user_service.logout_user(db_session, user_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": Message.MESSAGE_USER_LOGGED_OUT_SUCCESSFULLY},
    )


@router.get("/me", response_model=UserResponse, description="Get self user information")
async def get_self_user(
    request: Request, user_id: int, db_session: Session = Depends(get_db)
):
    """Get self user information"""
    if user_id != request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )
    user = user_service.get_user_by_id(db_session, user_id)
    return user


@router.put(
    "/me/password",
    response_model=ChangePasswordResponse,
    description="Update self user information",
)
async def update_self_user(
    request: Request,
    user_id: int,
    user_update_request: ChangePasswordRequest,
    db_session: Session = Depends(get_db),
):
    """Update self user information"""

    # Check permission
    if user_id != request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )

    # Check new password is not the same as old password
    if user_update_request.new_password == user_update_request.old_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Message.MESSAGE_NEW_PASSWORD_IS_THE_SAME_AS_OLD_PASSWORD,
        )

    # Change password
    response = user_service.change_password_user(
        db_session, user_id, user_update_request
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": response.message},
    )


@router.put(
    "/me/information",
    response_model=SelfUserInformationUpdateResponse,
    description="Update self user information",
)
async def update_self_user_information(
    request: Request,
    user_id: int,
    user_update_request: SelfUserInformationUpdateRequest,
    db_session: Session = Depends(get_db),
):
    """Update self user information"""
    # Check permission
    if user_id != request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )

    # Update self user information
    response = user_service.update_self_user_information(
        db_session, user_id, user_update_request
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": response.message},
    )


# API for admin
@router.get("/{user_id}", response_model=UserResponse, description="Get a user by ID")
async def get_user(
    request: Request, user_id: int, db_session: Session = Depends(get_db)
):
    """Get a user by ID"""

    # Check role permission
    roles = user_service.get_user_roles_by_id(db_session, request.state.user_id)
    role_ids = [role.id for role in roles]
    admin_role_id = RoleType.ADMIN.value
    logger.info(f"Role IDs: {role_ids}")
    print(f"{admin_role_id} not in {role_ids}")
    if admin_role_id not in role_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )
    # Get user by ID
    user = user_service.get_user_by_id(db_session, user_id)
    return user


@router.put(
    "/{user_id}", response_model=UserResponse, description="Update a user by ID"
)
async def update_user(
    request: Request,
    user_id: int,
    user_update_request: UserUpdateRequest,
    db_session: Session = Depends(get_db),
):
    # Check role permission
    roles = user_service.get_user_roles_by_id(db_session, request.state.user_id)
    role_ids = [role.id for role in roles]
    admin_role_id = RoleType.ADMIN.value
    logger.info(f"Role IDs: {role_ids}")
    if admin_role_id not in role_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )

    # Check roles of user to be updated
    user_roles = user_service.get_user_roles_by_id(db_session, user_id)
    user_role_ids = [role.id for role in user_roles]
    if admin_role_id in user_role_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )

    # Update user by ID
    logger.info(f"Updating user by ID: {user_id} with request: {user_update_request}")
    user = user_service.update_user_by_id(db_session, user_id, user_update_request)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Delete a user by ID",
)
async def delete_user(
    request: Request, user_id: int, db_session: Session = Depends(get_db)
):
    # Check role permission
    roles = user_service.get_user_roles_by_id(db_session, request.state.user_id)
    role_ids = [role.id for role in roles]
    admin_role_id = RoleType.ADMIN.value
    if admin_role_id not in role_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )

    # Check roles of user to be deleted
    user_roles = user_service.get_user_roles_by_id(db_session, user_id)
    user_role_ids = [role.id for role in user_roles]
    if admin_role_id in user_role_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )
    # Delete user by ID
    logger.info(f"Deleting user by ID: {user_id}")
    user_service.delete_user_by_id(db_session, user_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": Message.MESSAGE_USER_DELETED_SUCCESSFULLY},
    )
