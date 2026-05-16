"""
Users module Pydantic schemas.

Covers Profile, Settings, Security, and Public Profile UI screens.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ─── User Profile ────────────────────────────────────────
class UserProfileResponse(BaseModel):
    """Full user profile (My Profile screen — sidebar)."""
    id: int
    full_name: str
    email: str
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    credits: int = 0
    avg_rating: float = 0.0
    role: str = "user"
    auth_provider: str = "email"
    created_at: Optional[datetime] = None
    # Computed stats
    books_uploaded: int = 0
    books_available: int = 0
    books_borrowed: int = 0
    # Settings
    settings: Optional["UserSettingsResponse"] = None

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """
    Update profile form (edit icon on Profile screen).
    NOTE: email field is NOT included — email is IMMUTABLE.
    """
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    avatar_url: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"json_schema_extra": {
        "example": {
            "full_name": "Alex Morgan",
            "location": "Westheimer Rd. Santa Ana, Illinois",
            "latitude": 33.7455,
            "longitude": -117.8677,
        }
    }}


# ─── Public Profile ──────────────────────────────────────
class UserPublicProfileResponse(BaseModel):
    """Other People Profile screen — public view."""
    id: int
    full_name: str
    email: str
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    avg_rating: float = 0.0
    # Stats shown on public profile
    books_uploaded: int = 0
    books_available: int = 0
    books_borrowed: int = 0

    model_config = {"from_attributes": True}


# ─── Settings ────────────────────────────────────────────
class UserSettingsResponse(BaseModel):
    """Settings screen response — language and notification prefs."""
    language: str = "EN"
    email_notifications: bool = True
    new_message_alert: bool = True

    model_config = {"from_attributes": True}


class UserSettingsUpdateRequest(BaseModel):
    """Settings screen — update preferences."""
    language: Optional[str] = Field(None, max_length=10, description="EN or HE")
    email_notifications: Optional[bool] = None
    new_message_alert: Optional[bool] = None

    model_config = {"json_schema_extra": {
        "example": {
            "language": "EN",
            "email_notifications": True,
            "new_message_alert": True,
        }
    }}


# ─── Security ────────────────────────────────────────────
class ChangePasswordRequest(BaseModel):
    """Security screen — change password form."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")

    model_config = {"json_schema_extra": {
        "example": {
            "current_password": "OldPass123",
            "new_password": "NewPass456",
            "confirm_password": "NewPass456",
        }
    }}


class ChangePasswordResponse(BaseModel):
    """Response after successful password change."""
    message: str = "Password changed successfully"


class DeleteAccountResponse(BaseModel):
    """Response after account hard deletion."""
    message: str = "Account has been permanently deleted. We're sorry to see you go."


# Rebuild to resolve forward ref
UserProfileResponse.model_rebuild()
