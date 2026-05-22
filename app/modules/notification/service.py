"""
Notification module service.
Proxies to UserSettings for notification-specific preferences.
"""
from sqlalchemy.orm import Session
from app.modules.users.model import UserSettings, User
from app.modules.notification.schema import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
    NotificationResponse,
    NotificationPaginatedResponse,
)
from app.modules.notification.model import Notification
from app.shared.pagination import PaginationParams
from sqlalchemy import desc
import math
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

    def get_notifications(self, user: User, pagination: PaginationParams) -> NotificationPaginatedResponse:
        query = self.db.query(Notification).filter(Notification.user_id == user.id)
        total = query.count()
        notifications = query.order_by(desc(Notification.created_at)).offset(pagination.offset).limit(pagination.per_page).all()
        
        items = [NotificationResponse.model_validate(n) for n in notifications]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return NotificationPaginatedResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def get_notification_detail(self, user: User, notification_id: int) -> NotificationResponse:
        n = self.db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
        if not n:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        if not n.is_read:
            n.is_read = True
            self.db.commit()
            self.db.refresh(n)
            
        return NotificationResponse.model_validate(n)

    def mark_all_read(self, user: User) -> dict:
        self.db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == False).update({"is_read": True})
        self.db.commit()
        return {"message": "All notifications marked as read"}
