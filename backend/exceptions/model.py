from fastapi import status  # noqa

from backend.utils import constants


class BusinessBaseException(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)


class ObjectNotFoundException(BusinessBaseException):
    def __init__(self, message: str = constants.Message.MESSAGE_OBJECT_NOT_FOUND):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message=message)


class InvalidRequestException(BusinessBaseException):
    def __init__(self, message: str = constants.Message.MESSAGE_INVALID_REQUEST):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message)


class PermissionErrorException(BusinessBaseException):
    def __init__(self, message: str = constants.Message.MESSAGE_PERMISSION_DENIED):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, message=message)


class InvalidJoinFieldException(BusinessBaseException):
    def __init__(self, message: str = "Invalid join field"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message)


class NotImplementedException(BusinessBaseException):
    def __init__(self, message: str = "Not implemented"):
        super().__init__(status_code=status.HTTP_501_NOT_IMPLEMENTED, message=message)
