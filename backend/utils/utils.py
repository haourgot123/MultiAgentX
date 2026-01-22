import phonenumbers
from phonenumbers import NumberParseException

from backend.exceptions.model import InvalidJoinFieldException
from backend.utils.constants import PHONE_NUMBER_SUPPORT


def validate_and_normalize_phone(phone_number: str, country_code: str) -> str:
    if country_code not in PHONE_NUMBER_SUPPORT:
        raise InvalidJoinFieldException(message="Country not supported")

    try:
        parsed = phonenumbers.parse(phone_number, country_code)

        if not phonenumbers.is_valid_number(parsed):
            raise InvalidJoinFieldException(message="Invalid phone number")

        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    except NumberParseException:
        raise InvalidJoinFieldException(message="Invalid phone number format")
