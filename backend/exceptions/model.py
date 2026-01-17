from fastapi import status  # noqa
from backend.utils import constants


class BusinessBaseException(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)
        

class UserNotFoundException(BusinessBaseException):
    def __init__(self, message: str = constants.Message.USER_NOT_FOUND):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, message=message)
        
class UserNameAlreadyExistsException(BusinessBaseException):
    def __init__(self, message: str = constants.Message.USERNAME_ALREADY_EXISTS):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message)
    
class UserEmailAlreadyExistsException(BusinessBaseException):
    def __init__(self, message: str = constants.Message.USER_EMAIL_ALREADY_EXISTS):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message)
    
class InvalidPasswordException(BusinessBaseException):
    def __init__(self, message: str = constants.Message.INVALID_PASSWORD):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message)
    
class InvalidFullNameException(BusinessBaseException):
    def __init__(self, message: str = constants.Message.INVALID_FULL_NAME):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message)
    
class InvalidJoinFieldException(BusinessBaseException):
    def __init__(self, message: str = constants.Message.INVALID_JOIN_FIELD):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, message=message)