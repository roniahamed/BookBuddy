"""
Notification module schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences from Settings screen."""
    email_notifications: bool = True
    new_message_alert: bool = True

    model_config = {"from_attributes": True}


class NotificationPreferencesUpdateRequest(BaseModel):
    """Update notification preferences."""
    email_notifications: Optional[bool] = Field(None, description="Toggle email notifications")
    new_message_alert: Optional[bool] = Field(None, description="Toggle new message alerts")

    model_config = {"json_schema_extra": {
        "example": {
            "email_notifications": True,
            "new_message_alert": True,
        }
    }}

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class NotificationPaginatedResponse(BaseModel):
    items: List[NotificationResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False
