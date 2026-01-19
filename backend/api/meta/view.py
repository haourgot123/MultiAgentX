from fastapi import APIRouter

from backend.utils.constants import PHONE_NUMBER_SUPPORT

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("/phone-countries")
def get_phone_countries():
    return [
        {"code": code, "country": info["country"], "dial_code": info["dial_code"]}
        for code, info in PHONE_NUMBER_SUPPORT.items()
    ]
