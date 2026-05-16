"""
Users module service — business logic for user operations.
- Email is IMMUTABLE after registration
- Hard delete (no soft-delete)
"""
from sqlalchemy.orm import Session
from app.core.security import verify_password, get_password_hash
from app.modules.users.repository import UserRepository
from app.modules.users.model import User
from app.modules.users.schema import (
    UserProfileResponse, UserUpdateRequest, UserPublicProfileResponse,
    UserSettingsResponse, UserSettingsUpdateRequest,
    ChangePasswordRequest, ChangePasswordResponse, DeleteAccountResponse,
)
from app.modules.auth.exceptions import PasswordMismatchException
from app.core.exceptions import UserNotFoundException
from fastapi import HTTPException, status


class UserService:
    """Handles user-related business logic."""

    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def get_my_profile(self, user: User) -> UserProfileResponse:
        """Get full profile with stats and settings (Profile sidebar)."""
        stats = self.repo.get_user_profile_stats(user.id)
        settings = None
        if user.settings:
            settings = UserSettingsResponse.model_validate(user.settings)

        return UserProfileResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            avatar_url=user.avatar_url,
            location=user.location,
            latitude=user.latitude,
            longitude=user.longitude,
            credits=user.credits,
            avg_rating=user.avg_rating or 0.0,
            role=user.role,
            auth_provider=user.auth_provider,
            created_at=user.created_at,
            books_uploaded=stats["books_uploaded"],
            books_available=stats["books_available"],
            books_borrowed=stats["books_borrowed"],
            settings=settings,
        )

    def update_my_profile(self, user: User, data: UserUpdateRequest) -> UserProfileResponse:
        """
        Update own profile.
        EMAIL IS IMMUTABLE — reject if email is in the update payload.
        """
        update_data = data.model_dump(exclude_unset=True)

        # ─── EMAIL IMMUTABILITY: Reject email changes ────
        if "email" in update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email cannot be changed. Please contact support for assistance.",
            )

        updated_user = self.repo.update_user(user.id, update_data)
        return self.get_my_profile(updated_user)

    def get_public_profile(self, user_id: int) -> UserPublicProfileResponse:
        """Get another user's public profile (Other People Profile screen)."""
        user = self.repo.get_public_profile(user_id)
        if not user:
            raise UserNotFoundException()

        stats = self.repo.get_user_profile_stats(user_id)

        return UserPublicProfileResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            avatar_url=user.avatar_url,
            location=user.location,
            avg_rating=user.avg_rating or 0.0,
            books_uploaded=stats["books_uploaded"],
            books_available=stats["books_available"],
            books_borrowed=stats["books_borrowed"],
        )

    def get_settings(self, user: User) -> UserSettingsResponse:
        """Get user notification/language settings (Settings screen)."""
        settings = self.repo.get_settings(user.id)
        if not settings:
            raise HTTPException(status_code=404, detail="Settings not found")
        return UserSettingsResponse.model_validate(settings)

    def update_settings(self, user: User, data: UserSettingsUpdateRequest) -> UserSettingsResponse:
        """Update notification preferences (Settings screen toggles)."""
        update_data = data.model_dump(exclude_unset=True)
        settings = self.repo.update_settings(user.id, update_data)
        return UserSettingsResponse.model_validate(settings)

    def change_password(self, user: User, data: ChangePasswordRequest) -> ChangePasswordResponse:
        """Change password (Security screen)."""
        if user.auth_provider == "google" and not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google-authenticated accounts don't have a password to change.",
            )

        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        if data.new_password != data.confirm_password:
            raise PasswordMismatchException()

        password_hash = get_password_hash(data.new_password)
        self.repo.update_password(user.id, password_hash)
        return ChangePasswordResponse()

    def delete_account(self, user: User) -> DeleteAccountResponse:
        """
        HARD DELETE account — permanently removes user and all related data.
        CASCADE will clean up books, borrow_requests, reviews, wishlist, conversations, messages.
        """
        self.repo.hard_delete_user(user.id)
        return DeleteAccountResponse()
