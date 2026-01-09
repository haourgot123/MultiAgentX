from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from backend.utils.authentic import verify_access_token
from backend.utils.constants import Message
from backend.utils.dependency import get_db

from . import service as token_service

token_router = APIRouter(prefix="/token", tags=["Token"])


@token_router.post("/access", status_code=status.HTTP_200_OK)
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
            detail=Message.INVALID_REFRESH_TOKEN,
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
