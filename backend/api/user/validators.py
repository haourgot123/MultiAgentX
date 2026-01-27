"""
Reusable validators for user models.

This module provides common validation functions used across user-related models
to eliminate code duplication and ensure consistency.
"""

from datetime import datetime
from typing import Optional

from backend.exceptions.model import InvalidRequestException
from backend.utils.utils import validate_and_normalize_phone


def validate_password_strength(password: Optional[str]) -> Optional[str]:
    """Validate password meets minimum requirements.
    
    Args:
        password: Password string to validate.
        
    Returns:
        The validated password.
        
    Raises:
        InvalidRequestException: If password is too short.
    """
    if password is None:
        return None
        
    if len(password) < 8:
        raise InvalidRequestException(message="Password must be at least 8 characters long")
    
    return password


def validate_date_not_future(date_value: Optional[datetime]) -> Optional[datetime]:
    """Validate that a date is not in the future.
    
    Commonly used for date of birth validation.
    
    Args:
        date_value: Date to validate.
        
    Returns:
        The validated date.
        
    Raises:
        InvalidRequestException: If date is in the future.
    """
    if date_value is not None and date_value > datetime.now():
        raise InvalidRequestException(message="Date cannot be in the future")
    
    return date_value


def validate_phone_with_country(
    phone_number: Optional[str], country: Optional[str]
) -> Optional[str]:
    """Validate and normalize phone number with country code.
    
    Args:
        phone_number: Phone number to validate.
        country: Country code for validation context.
        
    Returns:
        Normalized phone number.
        
    Raises:
        InvalidRequestException: If phone number is provided without country code.
    """
    if phone_number:
        if not country:
            raise InvalidRequestException(
                message="Country code is required when providing phone number"
            )
        return validate_and_normalize_phone(phone_number, country)
    
    return phone_number
