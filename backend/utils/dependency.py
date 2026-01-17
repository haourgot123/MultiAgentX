from typing import Generator, Optional

from fastapi import Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.databases.db import SessionLocal
from backend.utils.authentic import verify_access_token
from backend.utils.constants import Message


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
