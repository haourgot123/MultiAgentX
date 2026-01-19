from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from backend.api.user.model import (
    LoginRequest,
    LoginResponse,
    UserCreateRequest,
    UserResponse,
)
from backend.api.user.service import user_service
from backend.utils.authentic import verify_access_token
from backend.utils.constants import Message, RoleType
from backend.utils.dependency import get_db

from . import service as token_service

router = APIRouter(prefix="/authentication", tags=["Authentication"])


@router.post("/access", status_code=status.HTTP_200_OK)
def generate_access_token(
    refresh_token: str = Body(..., embed=True),
    db_session: Session = Depends(get_db),
):
    """
    Generate new access token based on refresh token
    """
    # validate refresh token
    valid_token, token_info = verify_access_token(refresh_token)

    if not valid_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.MESSAGE_INVALID_REFRESH_TOKEN,
        )
    access_token = token_service.generate_access_token(
        db_session, token_info["email"], token_info["uid"], refresh_token
    )
    return {
        "user_id": token_info["uid"],
        "email": token_info["email"],
        "refresh_token": refresh_token,
        "access_token": access_token,
    }


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=LoginResponse,
    description="Login a user",
)
async def login(login_request: LoginRequest, db_session: Session = Depends(get_db)):
    response = user_service.login_user(db_session, login_request)
    return response


@router.post(
    "/register",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    description="Register a user",
)
async def register(
    register_request: UserCreateRequest, db_session: Session = Depends(get_db)
):
    if register_request.roles is not None:
        role_types = [role.value for role in RoleType]
        for role in register_request.roles:
            if role not in role_types:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=Message.MESSAGE_PERMISSION_DENIED,
                )
        # Check role permission
        if RoleType.ADMIN.value in register_request.roles:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=Message.MESSAGE_PERMISSION_DENIED,
            )
    else:
        register_request.roles = [RoleType.USER.value]
    response = user_service.create_new_user(db_session, register_request)
    return response
