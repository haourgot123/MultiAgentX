from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.api.user.model import (
    LoginRequest,
    UserRegisterRequest,
    UserRegisterResponse,
    UserResponse,
    UserUpdateRequest,
)
from backend.api.user.service import (
    create_new_user,
    delete_user_by_id,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    login_user,
    logout_user,
    update_user_by_id,
)
from backend.utils.constants import Message
from backend.utils.dependency import get_db
from backend.utils.error_message import InvalidRequestException

authentication_router = APIRouter(prefix="/user", tags=["User"])


@authentication_router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    description="Login a user",
)
async def login(login_request: LoginRequest, db_session: Session = Depends(get_db)):
    user = login_user(db_session, login_request)
    return UserResponse.model_validate(user)


@authentication_router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    description="Logout a user",
)
async def logout(user_id: int, db_session: Session = Depends(get_db)):
    user = logout_user(db_session, user_id)
    return UserResponse.model_validate(user)


@authentication_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRegisterResponse,
    description="Register a new user",
)
async def register_user(
    user_register_request: UserRegisterRequest, db_session: Session = Depends(get_db)
):
    is_user_email_exists = get_user_by_email(db_session, user_register_request.email)
    is_username_exists = get_user_by_username(
        db_session, user_register_request.username
    )
    if is_user_email_exists:
        raise InvalidRequestException(message=Message.USER_EMAIL_ALREADY_EXISTS)
    if is_username_exists:
        raise InvalidRequestException(message=Message.USERNAME_ALREADY_EXISTS)
    new_user = create_new_user(db_session, user_register_request)
    return UserRegisterResponse.model_validate(new_user)


@authentication_router.get(
    "/{user_id}", response_model=UserResponse, description="Get a user by ID"
)
async def get_user(user_id: int, db_session: Session = Depends(get_db)):
    user = get_user_by_id(db_session, user_id)
    return UserResponse.model_validate(user)


@authentication_router.put(
    "/{user_id}", response_model=UserResponse, description="Update a user by ID"
)
async def update_user(
    user_id: int,
    user_update_request: UserUpdateRequest,
    db_session: Session = Depends(get_db),
):
    user = update_user_by_id(db_session, user_id, user_update_request)
    return UserResponse.model_validate(user)


@authentication_router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    description="Delete a user by ID",
)
async def delete_user(user_id: int, db_session: Session = Depends(get_db)):
    user = delete_user_by_id(db_session, user_id)
    return UserResponse.model_validate(user)
