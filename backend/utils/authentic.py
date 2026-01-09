import hashlib
from time import time

import jwt
from fastapi import HTTPException, status
from loguru import logger

from backend.config.settings import _settings


def get_hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    return get_hash_password(password) == hashed_password


def create_refresh_token(user_id: str, user_email: str) -> str:
    rt = str(time())
    refresh_token_jwt_subject = "refresh_token"
    to_encode = {"user_id": user_id, "user_email": user_email}
    to_encode.update(
        {
            "exp_after": _settings.jwt.refresh_token_expire_minutes * 60,
            "iat": rt,
            "sub": refresh_token_jwt_subject,
        }
    )
    encoded_jwt = jwt.encode(
        payload=to_encode,
        key=_settings.jwt.secret_key,
        algorithm=_settings.jwt.algorithm,
    )
    return encoded_jwt


def create_access_token(data: dict) -> str:
    rt = str(time())
    access_token_jwt_subject = "access_token"
    to_encode = data.copy()
    to_encode.update(
        {
            "exp_after": _settings.jwt.access_token_expire_minutes * 60,
            "iat": rt,
            "sub": access_token_jwt_subject,
        }
    )
    encoded_jwt = jwt.encode(
        payload=to_encode,
        key=_settings.jwt.secret_key,
        algorithm=_settings.jwt.algorithm,
    )
    return encoded_jwt


def verify_access_token(token: str) -> dict:
    current_rt = str(time())
    token_info = None
    try:
        token_info = jwt.decode(
            token, _settings.jwt.secret_key, algorithms=[_settings.jwt.algorithm]
        )
    except Exception as e:
        logger.error(f"Error verifying access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    token_rt = token_info.get("exp_after")
    token_iat = token_info.get("iat")

    if token_rt < current_rt and (current_rt - token_rt) <= int(token_iat):
        return True, token_info
    else:
        return False, None
