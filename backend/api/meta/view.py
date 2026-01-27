from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.utils.constants import PHONE_NUMBER_SUPPORT

router = APIRouter(prefix="/meta", tags=["Meta"])


class PhoneCountryResponse(BaseModel):
    """Response model for phone country data."""

    code: str = Field(..., description="Country code (e.g., 'US', 'VN')")
    country: str = Field(..., description="Country name")
    dial_code: str = Field(..., description="International dial code (e.g., '+1', '+84')")


# Cache the phone countries list since it's static data
_PHONE_COUNTRIES_CACHE: List[PhoneCountryResponse] = [
    PhoneCountryResponse(
        code=code, country=info["country"], dial_code=info["dial_code"]
    )
    for code, info in PHONE_NUMBER_SUPPORT.items()
]


@router.get("/phone-countries", response_model=List[PhoneCountryResponse])
def get_phone_countries():
    """Get list of supported countries with their phone dial codes.
    
    Returns a cached list of countries with their ISO codes and international
    dial prefixes for phone number validation.
    
    Returns:
        List of phone country information including code, country name, and dial code.
    """
    return _PHONE_COUNTRIES_CACHE
