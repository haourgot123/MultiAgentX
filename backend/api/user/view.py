from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.api.user.model import (
    LoginRequest,
    LoginResponse,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from backend.api.user.service import user_service
from backend.utils.constants import Message
from backend.utils.dependency import get_db

authentication_router = APIRouter(prefix="/user", tags=["User"])


@authentication_router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=LoginResponse,
    description="Login a user",
)
async def login(login_request: LoginRequest, db_session: Session = Depends(get_db)):
    user = user_service.login_user(db_session, login_request)
    return user


@authentication_router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    description="Logout a user",
)
async def logout(user_id: int, db_session: Session = Depends(get_db)):
    user_service.logout_user(db_session, user_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": Message.USER_LOGGED_OUT_SUCCESSFULLY},
    )


@authentication_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    description="Register a new user",
)
async def register_user(
    user_register_request: UserRegisterRequest, db_session: Session = Depends(get_db)
):

    user = user_service.create_new_user(db_session, user_register_request)
    return user


@authentication_router.get(
    "/{user_id}", response_model=UserResponse, description="Get a user by ID"
)
async def get_user(user_id: int, db_session: Session = Depends(get_db)):
    user = user_service.get_user_by_id(db_session, user_id)
    return user


@authentication_router.put(
    "/{user_id}", response_model=UserResponse, description="Update a user by ID"
)
async def update_user(
    user_id: int,
    user_update_request: UserUpdateRequest,
    db_session: Session = Depends(get_db),
):
    user = user_service.update_user_by_id(db_session, user_id, user_update_request)
    return user


@authentication_router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    description="Delete a user by ID",
)
async def delete_user(user_id: int, db_session: Session = Depends(get_db)):

    try:
        user_service.delete_user_by_id(db_session, user_id)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": Message.USER_DELETED_SUCCESSFULLY},
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
