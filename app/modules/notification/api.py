"""
Notification module API endpoints.

Covers:
- GET  /notifications/preferences — Get notification settings
- PUT  /notifications/preferences — Update notification settings
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.notification.service import NotificationService
from app.modules.notification.schema import (
    NotificationPreferencesResponse,
    NotificationPreferencesUpdateRequest,
)

router = APIRouter()


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Get notification preferences",
    description=(
        "Get current notification settings: email notifications and new message alerts. "
        "Corresponds to the notification toggles on the Settings screen."
    ),
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    return service.get_preferences(current_user)


@router.put(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Update notification preferences",
    description=(
        "Update notification settings. Only provided fields are updated. "
        "Controls Email Notification and New Message Alert toggles."
    ),
)
async def update_preferences(
    data: NotificationPreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    return service.update_preferences(current_user, data)
