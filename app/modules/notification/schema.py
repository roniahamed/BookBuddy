"""
Notification module schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional


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
