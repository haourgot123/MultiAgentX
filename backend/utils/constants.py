from enum import Enum


class Message:
    MESSAGE_INVALID_REQUEST = "Oops! Invalid request"
    MESSAGE_INVALID_TOKEN = "Oops! Invalid token"
    MESSAGE_DELETED_SUCCESSFULLY = "Deleted success"
    MESSAGE_USER_DELETED_SUCCESSFULLY = "User deleted successfully"
    MESSAGE_USERNAME_ALREADY_EXISTS = "Oops! Username already exists"
    MESSAGE_USER_EMAIL_ALREADY_EXISTS = "Oops! User email already exists"
    MESSAGE_USER_CREATED_SUCCESSFULLY = "User created successfully"
    MESSAGE_USER_NOT_FOUND = "Oops! User not found"
    MESSAGE_USER_DELETED = "Oops! User deleted"
    MESSAGE_INVALID_PASSWORD = "Oops! Invalid password"
    MESSAGE_PASSWORD_DO_NOT_MATCH = "Oops! Password do not match"
    MESSAGE_NEW_PASSWORD_IS_THE_SAME_AS_OLD_PASSWORD = (
        "Oops! New password is the same as old password"
    )
    MESSAGE_INVALID_FULL_NAME = "Oops! Invalid full name"
    MESSAGE_INVALID_REFRESH_TOKEN = "Oops! Invalid refresh token"
    MESSAGE_LOGIN_FAILED = "Oops! Please check your username or password"
    MESSAGE_PASSWORD_CHANGED_SUCCESSFULLY = "Password changed successfully"
    MESSAGE_USER_LOGGED_OUT_SUCCESSFULLY = "User logged out successfully"
    MESSAGE_PERMISSION_DENIED = "Oops! You are not authorized to access this resource"
    MESSAGE_INTERNAL_SERVER_ERROR = "Oops! Internal server error"
    MESSAGE_INVALID_JOIN_FIELD = "Oops! Invalid join field"
    MESSAGE_USER_ALREADY_DELETED = "Oops! User already deleted"
    MESSAGE_USER_INFORMATION_UPDATED_SUCCESSFULLY = (
        "User information updated successfully"
    )
    MESSAGE_INVALID_PHONE_NUMBER = "Oops! Invalid phone number"
    MESSAGE_VALUE_ERROR = "Oops! Value error"

    MESSAGE_OBJECT_NOT_FOUND = "Oops! Object Not Found"


class TokenType(Enum):
    REFRESH = 1
    ACCESS = 2


class RoleType(Enum):
    ADMIN = 1
    USER = 2


PHONE_NUMBER_SUPPORT = {
    "VN": {"country": "Vietnam", "dial_code": "+84", "region": "Asia"},
    "US": {"country": "United States", "dial_code": "+1", "region": "North America"},
    "JP": {"country": "Japan", "dial_code": "+81", "region": "Asia"},
    "KR": {"country": "South Korea", "dial_code": "+82", "region": "Asia"},
    "CN": {"country": "China", "dial_code": "+86", "region": "Asia"},
    "TW": {"country": "Taiwan", "dial_code": "+886", "region": "Asia"},
    "HK": {"country": "Hong Kong", "dial_code": "+852", "region": "Asia"},
    "SG": {"country": "Singapore", "dial_code": "+65", "region": "Asia"},
    "TH": {"country": "Thailand", "dial_code": "+66", "region": "Asia"},
    "ID": {"country": "Indonesia", "dial_code": "+62", "region": "Asia"},
    "MY": {"country": "Malaysia", "dial_code": "+60", "region": "Asia"},
    "PH": {"country": "Philippines", "dial_code": "+63", "region": "Asia"},
    "IN": {"country": "India", "dial_code": "+91", "region": "Asia"},
    "AU": {"country": "Australia", "dial_code": "+61", "region": "Oceania"},
    "GB": {"country": "United Kingdom", "dial_code": "+44", "region": "Europe"},
    "FR": {"country": "France", "dial_code": "+33", "region": "Europe"},
    "DE": {"country": "Germany", "dial_code": "+49", "region": "Europe"},
    "IT": {"country": "Italy", "dial_code": "+39", "region": "Europe"},
    "ES": {"country": "Spain", "dial_code": "+34", "region": "Europe"},
    "NL": {"country": "Netherlands", "dial_code": "+31", "region": "Europe"},
    "RU": {"country": "Russia", "dial_code": "+7", "region": "Europe"},
    "BR": {"country": "Brazil", "dial_code": "+55", "region": "South America"},
}
