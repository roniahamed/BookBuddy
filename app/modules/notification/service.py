"""
Notification module service.
Proxies to UserSettings for notification-specific preferences.
"""
from sqlalchemy.orm import Session
from app.modules.users.model import UserSettings, User
from app.modules.notification.schema import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
)
from fastapi import HTTPException


class NotificationService:
    """Handles notification preference logic."""

    def __init__(self, db: Session):
        self.db = db

    def get_preferences(self, user: User) -> NotificationPreferencesResponse:
        """Get current notification preferences."""
        settings = self.db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        if not settings:
            raise HTTPException(status_code=404, detail="Settings not found")

        return NotificationPreferencesResponse(
            email_notifications=settings.email_notifications,
            new_message_alert=settings.new_message_alert,
        )

    def update_preferences(
        self, user: User, data: NotificationPreferencesUpdateRequest
    ) -> NotificationPreferencesResponse:
        """Update notification preferences."""
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            self.db.query(UserSettings).filter(UserSettings.user_id == user.id).update(update_data)
            self.db.commit()

        return self.get_preferences(user)
