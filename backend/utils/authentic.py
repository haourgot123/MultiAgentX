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


def create_refresh_token(uid, email):
    rt = int(time())
    expire = int(_settings.jwt.refresh_token_expire_minutes) * 60
    token = jwt.encode(
        {
            "rt": rt,
            "expire_after": expire,
            "uid": uid,
            "email": email,
            "tok_type": "refresh",
        },
        str(_settings.jwt.secret_key),
        algorithm=_settings.jwt.algorithm,
    )
    return token


def create_access_token(*, data: dict):
    rt = int(time())
    to_encode = data.copy()
    expire = int(_settings.jwt.access_token_expire_minutes) * 60
    to_encode.update(
        {"rt": rt, "expire_after": expire, "sub": "access_token"}
    )
    encoded_jwt = jwt.encode(
        to_encode, str(_settings.jwt.secret_key), algorithm=_settings.jwt.algorithm
    )
    return encoded_jwt


def verify_access_token(token: str) -> dict:
    # Returns Is_Valid, user_id
    rt = int(time())
    token_raw = None
    try:
        token_raw = jwt.decode(
            token, _settings.jwt.secret_key, algorithms=_settings.jwt.algorithm
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    tk_rt = token_raw["rt"]
    tk_ex = token_raw["expire_after"]

    # validate time expired token
    if tk_rt <= rt and (rt - tk_rt) <= int(tk_ex):
        return True, token_raw
    else:
        # token is outdated
        return False, None