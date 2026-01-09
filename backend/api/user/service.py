from typing import Optional

from fastapi import Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.api.token.service import generate_tokens
from backend.api.user.model import (
    LoginRequest,
    User,
    UserRegisterRequest,
    UserRegisterResponse,
    UserResponse,
    UserUpdateRequest,
)
from backend.databases.db import get_by_filter, get_by_id, get_utc_now, insert_row
from backend.utils.authentic import verify_access_token
from backend.utils.constants import Message
from backend.utils.error_message import InvalidRequestException


def get_current_user(request: Request, token: Optional[str] = Header(None)):
    if "Token" in request.headers:
        token = request.headers["Token"]
    elif "Authorization" in request.headers:
        token = request.headers["Authorization"].split()[-1]

    valid_token, data = verify_access_token(token)

    if not valid_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Message.INVALID_TOKEN,
        )
    request.state.email = data["email"]
    request.state.user_id = data["user_id"]


def get_user_by_email(db_session: Session, email: str):
    return get_by_filter(
        db_session,
        User,
        filters=[User.email == email.lower(), User.deleted.is_(False)],
        first=True,
    )


def get_user_by_username(db_session: Session, username: str):
    return get_by_filter(
        db_session,
        User,
        filters=[User.username == username.lower(), User.deleted.is_(False)],
        first=True,
    )


def create_new_user(db_session: Session, user_register_request: UserRegisterRequest):
    new_user = User(
        email=user_register_request.email.lower(),
        full_name=user_register_request.full_name,
        username=user_register_request.username.lower(),
    )
    if user_register_request.password:
        new_user.set_password(user_register_request.password)
    insert_row(db_session, new_user)

    new_user.created_at = get_utc_now()
    new_user.updated_at = get_utc_now()
    db_session.commit()
    db_session.refresh(new_user)
    return UserRegisterResponse.model_validate(new_user)


def get_user_by_id(db_session: Session, user_id: int):
    return get_by_id(db_session, User, user_id)


def update_user_by_id(
    db_session: Session, user_id: int, user_update_request: UserUpdateRequest
):
    user = get_user_by_id(db_session, user_id)
    if not user:
        raise InvalidRequestException(message=Message.USER_NOT_FOUND)
    user.email = (
        user_update_request.email.lower() if user_update_request.email else user.email
    )
    user.full_name = (
        user_update_request.full_name
        if user_update_request.full_name
        else user.full_name
    )
    user.username = (
        user_update_request.username.lower()
        if user_update_request.username
        else user.username
    )
    user.roles = user_update_request.roles if user_update_request.roles else user.roles
    user.password = (
        user_update_request.password if user_update_request.password else user.password
    )
    user.updated_at = get_utc_now()
    db_session.commit()
    db_session.refresh(user)
    return UserResponse.model_validate(user)


def delete_user_by_id(db_session: Session, user_id: int):
    user = get_user_by_id(db_session, user_id)
    if not user:
        raise InvalidRequestException(message=Message.USER_NOT_FOUND)
    user.deleted = True
    db_session.commit()
    db_session.refresh(user)
    return user


def login_user(db_session: Session, login_request: LoginRequest):
    user = get_user_by_username(db_session, login_request.username)
    if not user:
        raise InvalidRequestException(message=Message.USER_NOT_FOUND)
    if not user.check_password(login_request.password):
        raise InvalidRequestException(message=Message.INVALID_PASSWORD)

    refresh_token, access_token = generate_tokens(db_session, user.id, user.email)
    return user


def logout_user(db_session: Session, user_id: int):
    user = get_user_by_id(db_session, user_id)
    if not user:
        raise InvalidRequestException(message=Message.USER_NOT_FOUND)
    user.last_login = get_utc_now()
    db_session.commit()
    db_session.refresh(user)
    return user
