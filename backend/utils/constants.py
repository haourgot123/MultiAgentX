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
    INVALID_PASSWORD = "Invalid password"
    INVALID_REFRESH_TOKEN = "Invalid refresh token"


class TokenType(Enum):
    REFRESH = "refresh"
    ACCESS = "access"


class RoleEnum(Enum):
    ADMIN = "admin"
    USER = "user"
    DEVELOPER = "developer"


class ResourceFactory(Enum):
    SQL_DB = "postgres"
    VECTOR_DB = "qdrant"
