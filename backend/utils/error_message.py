from fastapi import status  # noqa
from starlette.exceptions import HTTPException

from backend.utils import constants


class InvalidRequestException(HTTPException):
    def __init__(self, message=constants.Message.INVALID_REQUEST):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
