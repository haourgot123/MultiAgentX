from enum import Enum


class Message:
    INVALID_REQUEST = "Invalid request"
    INVALID_TOKEN = "Invalid token"
    DELETED_SUCCESSFULLY = "Deleted success"
    USER_DELETED_SUCCESSFULLY = "User deleted successfully"
    USERNAME_ALREADY_EXISTS = "Username already exists"
    USER_EMAIL_ALREADY_EXISTS = "User email already exists"
    USER_CREATED_SUCCESSFULLY = "User created successfully"
    USER_NOT_FOUND = "User not found"
    USER_DELETED = "User deleted"
    INVALID_PASSWORD = "Invalid password"
    INVALID_FULL_NAME = "Invalid full name"
    INVALID_REFRESH_TOKEN = "Invalid refresh token"
    LOGIN_FAILED = "Please check your username or password"
    PASSWORD_CHANGED_SUCCESSFULLY = "Password changed successfully"
    USER_LOGGED_OUT_SUCCESSFULLY = "User logged out successfully"
    INTERNAL_SERVER_ERROR = "Internal server error"
    INVALID_JOIN_FIELD = "Invalid join field"


class TokenType(Enum):
    REFRESH = 1
    ACCESS = 2
