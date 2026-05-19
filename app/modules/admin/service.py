"""
Admin module service layer — covers:
- AdminConfigService: typed config access with DB-backed defaults (existing)
- AdminManagementService: user/book/review management + broadcast notifications
"""
import math
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.modules.admin.repository import AdminConfigRepository, AdminManagementRepository
from app.modules.admin.schema import (
    AppConfigResponse, AppConfigListResponse, AppConfigUpdateRequest,
    AdminStatsResponse,
    AdminUserListItem, AdminUserDetailResponse, AdminUserSuspendRequest,
    AdminUserActionResponse, AdminUserListResponse,
    AdminBookListItem, AdminBookUpdateRequest, AdminBookActionResponse, AdminBookListResponse,
    AdminReviewListItem, AdminReviewActionResponse, AdminReviewListResponse,
    AdminBroadcastNotificationRequest, AdminBroadcastNotificationResponse,
)

logger = logging.getLogger(__name__)

# ─── Default Configs ──────────────────────────────────────
DEFAULT_CONFIGS: dict[str, tuple[str, str]] = {
    "borrow_reward_borrower_points": ("5", "Points awarded to borrower on confirmed return"),
    "borrow_reward_lender_points": ("10", "Points awarded to lender on confirmed return"),
    "otp_expiry_minutes": ("15", "OTP code validity duration in minutes"),
    "max_borrow_requests_per_user": ("5", "Maximum active borrow requests per user"),
    "default_borrow_duration_days": ("30", "Default borrow period in days"),
    "nearby_radius_km": ("50", "Default nearby search radius in km"),
    "default_language": ("EN", "Default platform language (EN or HE)"),
    "due_date_reminder_days_before": ("2", "Days before due date to send reminder"),
    "overdue_check_interval_hours": ("6", "Hours between overdue book checks"),
}


# ─── Existing Config Service (preserved) ─────────────────

class AdminConfigService:
    """Provides typed config access. Falls back to defaults if key not in DB."""

    def __init__(self, db: Session):
        self.repo = AdminConfigRepository(db)

    def get(self, key: str, default: str = "") -> str:
        """Get config value as string."""
        config = self.repo.get_by_key(key)
        if config:
            return config.value
        # Fallback to hardcoded defaults
        if key in DEFAULT_CONFIGS:
            return DEFAULT_CONFIGS[key][0]
        return default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get config value as integer."""
        try:
            return int(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get config value as float."""
        try:
            return float(self.get(key, str(default)))
        except (ValueError, TypeError):
            return default

    def list_all(self) -> AppConfigListResponse:
        """List all configs."""
        configs = self.repo.get_all()
        return AppConfigListResponse(
            items=[AppConfigResponse.model_validate(c) for c in configs]
        )

    def get_config(self, key: str) -> AppConfigResponse:
        """Get single config."""
        config = self.repo.get_by_key(key)
        if not config:
            raise HTTPException(status_code=404, detail=f"Config '{key}' not found")
        return AppConfigResponse.model_validate(config)

    def update_config(self, key: str, data: AppConfigUpdateRequest) -> AppConfigResponse:
        """Update a config value."""
        config = self.repo.set_value(key, data.value)
        return AppConfigResponse.model_validate(config)

    def seed_defaults(self) -> None:
        """Seed all default configs on startup."""
        self.repo.seed_defaults(DEFAULT_CONFIGS)


# ─── Admin Management Service ─────────────────────────────

class AdminManagementService:
    """Business logic for admin user/book/review management + notifications."""

    def __init__(self, db: Session):
        self.repo = AdminManagementRepository(db)
        self.db = db

    # ── Stats ─────────────────────────────────────────────

    def get_stats(self) -> AdminStatsResponse:
        stats = self.repo.get_platform_stats()
        return AdminStatsResponse(**stats)

    # ── User Management ───────────────────────────────────

    def list_users(
        self,
        search=None,
        role=None,
        is_active=None,
        page: int = 1,
        size: int = 20,
    ) -> AdminUserListResponse:
        users, total = self.repo.get_all_users(search, role, is_active, page, size)
        items = []
        for user in users:
            stats = self.repo.get_user_stats(user)
            items.append(AdminUserListItem(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                credits=user.credits,
                avg_rating=user.avg_rating,
                books_uploaded=stats["books_uploaded"],
                created_at=user.created_at,
            ))
        pages = math.ceil(total / size) if total > 0 else 1
        return AdminUserListResponse(items=items, total=total, page=page, size=size, pages=pages)

    def get_user_detail(self, user_id: int) -> AdminUserDetailResponse:
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        stats = self.repo.get_user_stats(user)
        return AdminUserDetailResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            credits=user.credits,
            avg_rating=user.avg_rating,
            location=user.location,
            latitude=user.latitude,
            longitude=user.longitude,
            auth_provider=user.auth_provider,
            firebase_uid=user.firebase_uid,
            created_at=user.created_at,
            updated_at=user.updated_at,
            **stats,
        )

    def suspend_user(self, user_id: int, data: AdminUserSuspendRequest, admin_user) -> AdminUserActionResponse:
        """Suspend a user. Cannot suspend another admin."""
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user_id == admin_user.id:
            raise HTTPException(status_code=400, detail="You cannot suspend your own account.")
        if user.role == "admin":
            raise HTTPException(status_code=403, detail="Cannot suspend another admin")
        if not user.is_active:
            raise HTTPException(status_code=409, detail="User is already suspended")

        self.repo.suspend_user(user_id)

        # Fire FCM + email notification to the suspended user
        reason = data.reason or "Your account has been suspended. Please contact support."
        self._notify_user(
            user=user,
            title="Account Suspended",
            body=reason,
        )

        return AdminUserActionResponse(
            message=f"User '{user.email}' has been suspended.",
            user_id=user_id,
            is_active=False,
        )

    def activate_user(self, user_id: int, admin_user) -> AdminUserActionResponse:
        """Reactivate a suspended user."""
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_active:
            raise HTTPException(status_code=409, detail="User is already active")

        self.repo.activate_user(user_id)

        # Notify user of reactivation
        self._notify_user(
            user=user,
            title="Account Reactivated",
            body="Great news! Your BookBuddy account has been reactivated. Welcome back!",
        )

        return AdminUserActionResponse(
            message=f"User '{user.email}' has been reactivated.",
            user_id=user_id,
            is_active=True,
        )

    def delete_user(self, user_id: int, admin_user) -> dict:
        """Hard-delete a user and all their data."""
        user = self.repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.role == "admin":
            raise HTTPException(status_code=403, detail="Cannot delete another admin account")

        email = user.email
        deleted = self.repo.delete_user(user_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete user")
        return {"message": f"User '{email}' and all related data have been permanently deleted."}

    # ── Book Management ───────────────────────────────────

    def list_books(
        self,
        search=None,
        availability=None,
        genre_id=None,
        page: int = 1,
        size: int = 20,
    ) -> AdminBookListResponse:
        books, total = self.repo.get_all_books(search, availability, genre_id, page, size)
        items = []
        for book in books:
            items.append(AdminBookListItem(
                id=book.id,
                title=book.title,
                author_name=book.author_name,
                front_cover_url=book.front_cover_url,
                back_cover_url=book.back_cover_url,
                owner_id=book.owner_id,
                owner_name=book.owner.full_name if book.owner else "",
                owner_email=book.owner.email if book.owner else "",
                genre_name=book.genre.name if book.genre else None,
                availability=book.availability,
                condition=book.condition,
                avg_rating=book.avg_rating,
                created_at=book.created_at,
            ))
        pages = math.ceil(total / size) if total > 0 else 1
        return AdminBookListResponse(items=items, total=total, page=page, size=size, pages=pages)

    def update_book(self, book_id: int, data: AdminBookUpdateRequest) -> AdminBookActionResponse:
        book = self.repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        updated = self.repo.update_book(book_id, data.availability, data.description)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update book")

        # Notify owner if book was set to unavailable
        if data.availability == "unavailable" and book.owner:
            self._notify_user(
                user=book.owner,
                title="Book Listing Updated",
                body=f"Your book '{book.title}' has been marked unavailable by an admin.",
            )

        return AdminBookActionResponse(
            message=f"Book '{updated.title}' has been updated.",
            book_id=book_id,
        )

    def delete_book(self, book_id: int) -> AdminBookActionResponse:
        book = self.repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        title = book.title
        owner = book.owner

        deleted, owner_id = self.repo.delete_book(book_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete book")

        # Notify owner of removal
        if owner:
            self._notify_user(
                user=owner,
                title="Book Listing Removed",
                body=f"Your book listing '{title}' has been removed by an admin for policy violations.",
            )

        return AdminBookActionResponse(
            message=f"Book '{title}' has been permanently removed.",
            book_id=book_id,
        )

    # ── Reviews Management ────────────────────────────────

    def list_reviews(
        self,
        book_id=None,
        min_rating=None,
        max_rating=None,
        page: int = 1,
        size: int = 20,
    ) -> AdminReviewListResponse:
        reviews, total = self.repo.get_all_reviews(book_id, min_rating, max_rating, page, size)
        items = []
        for review in reviews:
            items.append(AdminReviewListItem(
                id=review.id,
                book_id=review.book_id,
                book_title=review.book.title if review.book else "",
                reviewer_id=review.reviewer_id,
                reviewer_name=review.reviewer.full_name if review.reviewer else "",
                reviewer_avatar_url=review.reviewer.avatar_url if review.reviewer else None,
                reviewee_id=review.reviewee_id,
                reviewee_name=review.reviewee.full_name if review.reviewee else "",
                rating=review.rating,
                review_text=review.review_text,
                created_at=review.created_at,
            ))
        pages = math.ceil(total / size) if total > 0 else 1
        return AdminReviewListResponse(items=items, total=total, page=page, size=size, pages=pages)

    def delete_review(self, review_id: int) -> AdminReviewActionResponse:
        review = self.repo.get_review_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        deleted, book_id, reviewee_id = self.repo.delete_review_and_recalculate(review_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete review")

        return AdminReviewActionResponse(
            message=f"Review #{review_id} has been removed and ratings recalculated.",
            review_id=review_id,
        )

    # ── Notifications Broadcast ───────────────────────────

    def broadcast_notification(
        self,
        data: AdminBroadcastNotificationRequest,
    ) -> AdminBroadcastNotificationResponse:
        """
        Send FCM push + email notification to a single user or all active users.
        Gracefully handles Celery/FCM being unavailable.
        """
        from app.modules.users.model import User as UserModel
        from app.modules.users.model import UserFCMToken

        if data.target == "user":
            if not data.user_id:
                raise HTTPException(
                    status_code=422,
                    detail="user_id is required when target='user'",
                )
            user = self.repo.get_user_by_id(data.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            recipients = [user]
        else:
            recipients = self.repo.get_all_active_users()

        push_sent = False
        email_sent = False
        recipients_count = len(recipients)

        for user in recipients:
            # ── FCM Push ──────────────────────────────────
            if data.send_push:
                try:
                    from app.background.tasks import send_push_notification_task
                    send_push_notification_task.delay(user.id, data.title, data.body)
                    push_sent = True
                except Exception as exc:
                    logger.warning("FCM push failed for user %s: %s", user.id, exc)

            # ── Email ─────────────────────────────────────
            if data.send_email and user.email:
                try:
                    from app.background.tasks import send_notification_email_task
                    send_notification_email_task.delay(
                        user.email,
                        data.title,
                        data.body,
                        user.full_name,
                    )
                    email_sent = True
                except Exception as exc:
                    logger.warning("Email notification failed for user %s: %s", user.id, exc)

        return AdminBroadcastNotificationResponse(
            message=f"Notification dispatched to {recipients_count} recipient(s).",
            recipients_count=recipients_count,
            push_sent=push_sent,
            email_sent=email_sent,
        )

    # ── Internal Helper ───────────────────────────────────

    def _notify_user(self, user, title: str, body: str) -> None:
        """Fire-and-forget FCM + email notification to a single user."""
        try:
            from app.background.tasks import send_push_notification_task
            send_push_notification_task.delay(user.id, title, body)
        except Exception as exc:
            logger.warning("FCM notify failed for user %s: %s", user.id, exc)

        try:
            from app.background.tasks import send_notification_email_task
            send_notification_email_task.delay(user.email, title, body, user.full_name)
        except Exception as exc:
            logger.warning("Email notify failed for user %s: %s", user.id, exc)
