"""
Shared validators used across modules.
"""
import re
from fastapi import HTTPException, status


def validate_email(email: str) -> str:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email format"
        )
    return email.lower().strip()


def validate_password(password: str) -> str:
    """Validate password strength: min 8 chars, 1 upper, 1 lower, 1 digit."""
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long"
        )
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one uppercase letter"
        )
    if not re.search(r'[a-z]', password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one lowercase letter"
        )
    if not re.search(r'[0-9]', password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must contain at least one digit"
        )
    return password


def validate_coordinates(latitude: float = None, longitude: float = None):
    """Validate GPS coordinates are within valid ranges."""
    if latitude is not None and (latitude < -90 or latitude > 90):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Latitude must be between -90 and 90"
        )
    if longitude is not None and (longitude < -180 or longitude > 180):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Longitude must be between -180 and 180"
        )


def validate_rating(rating: float) -> float:
    """Validate rating is between 0 and 5."""
    if rating < 0 or rating > 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rating must be between 0 and 5"
        )
    return round(rating, 2)
