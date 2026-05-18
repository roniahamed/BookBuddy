"""
Admin module API — manage application configuration and platform data.
All endpoints require admin role JWT.

Covers:
Config Management (existing):
- GET    /admin/config                   — List all configs
- GET    /admin/config/{key}             — Get config by key
- PATCH  /admin/config/{key}             — Update config value

Platform Stats:
- GET    /admin/stats                    — Dashboard overview numbers

User Management:
- GET    /admin/users                    — List all users (search, role, is_active, paginated)
- GET    /admin/users/{user_id}          — User detail
- PATCH  /admin/users/{user_id}/suspend  — Suspend user
- PATCH  /admin/users/{user_id}/activate — Reactivate user
- DELETE /admin/users/{user_id}          — Delete user (hard)

Book Management:
- GET    /admin/books                    — List all books (search, availability, genre, paginated)
- PATCH  /admin/books/{book_id}          — Update book (availability override, description)
- DELETE /admin/books/{book_id}          — Remove book listing

Reviews & Ratings Monitoring:
- GET    /admin/reviews                  — List all reviews (book_id, rating range, paginated)
- DELETE /admin/reviews/{review_id}      — Delete review + recalculate avg ratings

Notifications Management:
- POST   /admin/notifications/broadcast  — Broadcast FCM push + email to all or single user
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.admin.service import AdminConfigService, AdminManagementService
from app.modules.admin.schema import (
    AppConfigResponse, AppConfigUpdateRequest, AppConfigListResponse,
    AdminStatsResponse,
    AdminUserListResponse, AdminUserDetailResponse,
    AdminUserSuspendRequest, AdminUserActionResponse,
    AdminBookListResponse, AdminBookUpdateRequest, AdminBookActionResponse,
    AdminReviewListResponse, AdminReviewActionResponse,
    AdminBroadcastNotificationRequest, AdminBroadcastNotificationResponse,
)

router = APIRouter()


# ─── Auth Guard ───────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: only admin users can access admin endpoints."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ═══════════════════════════════════════════════════════════
# CONFIG MANAGEMENT (existing)
# ═══════════════════════════════════════════════════════════

@router.get(
    "/config",
    response_model=AppConfigListResponse,
    summary="List all configurations",
    description=(
        "Get all admin-configurable settings: borrow points, OTP expiry, "
        "nearby radius, etc. Only accessible by admin users."
    ),
)
async def list_configs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminConfigService(db)
    return service.list_all()


@router.get(
    "/config/{key}",
    response_model=AppConfigResponse,
    summary="Get a configuration",
    description="Get a single configuration value by key.",
    responses={404: {"description": "Config key not found"}},
)
async def get_config(
    key: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminConfigService(db)
    return service.get_config(key)


@router.patch(
    "/config/{key}",
    response_model=AppConfigResponse,
    summary="Update a configuration",
    description=(
        "Update a configuration value. Examples:\n"
        "- `borrow_reward_borrower_points` = 5 (points for borrower on confirmed return)\n"
        "- `borrow_reward_lender_points` = 10 (points for lender)\n"
        "- `otp_expiry_minutes` = 15\n"
        "- `nearby_radius_km` = 50\n"
        "- `default_borrow_duration_days` = 30"
    ),
)
async def update_config(
    key: str,
    data: AppConfigUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminConfigService(db)
    return service.update_config(key, data)


# ═══════════════════════════════════════════════════════════
# PLATFORM STATS
# ═══════════════════════════════════════════════════════════

@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Platform overview stats",
    description=(
        "Get a real-time snapshot of the platform: total users, active users, suspended users, "
        "book counts, borrow request statuses (including overdue), and review metrics. "
        "Use this for the admin dashboard home screen."
    ),
)
async def get_platform_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.get_stats()


# ═══════════════════════════════════════════════════════════
# USER MANAGEMENT
# ═══════════════════════════════════════════════════════════

@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List all users",
    description=(
        "Paginated list of all registered users with optional filters: "
        "`search` (name/email), `role` (user/admin), `is_active` (true/false). "
        "Includes per-user stats: books uploaded, credits, avg rating."
    ),
)
async def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[str] = Query(None, description="Filter by role: 'user' or 'admin'"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.list_users(search, role, is_active, page, size)


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    summary="Get user detail",
    description=(
        "Full user detail for admin view: all profile fields, role, activity status, credits, "
        "avg rating, and computed stats (books uploaded/available, borrows, reviews written/received)."
    ),
    responses={404: {"description": "User not found"}},
)
async def get_user_detail(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.get_user_detail(user_id)


@router.patch(
    "/users/{user_id}/suspend",
    response_model=AdminUserActionResponse,
    summary="Suspend a user",
    description=(
        "Deactivate a user account — sets `is_active=false`, preventing login. "
        "Use for users who engage in unethical behavior (e.g., repeatedly not returning books). "
        "An optional reason can be provided; the user will receive an FCM push + email notification. "
        "Cannot suspend another admin account."
    ),
    responses={
        403: {"description": "Cannot suspend another admin"},
        404: {"description": "User not found"},
        409: {"description": "User is already suspended"},
    },
)
async def suspend_user(
    user_id: int,
    data: AdminUserSuspendRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.suspend_user(user_id, data, admin)


@router.patch(
    "/users/{user_id}/activate",
    response_model=AdminUserActionResponse,
    summary="Reactivate a suspended user",
    description=(
        "Restore a previously suspended user account — sets `is_active=true`. "
        "The user will receive an FCM push + email notification that their account is restored."
    ),
    responses={
        404: {"description": "User not found"},
        409: {"description": "User is already active"},
    },
)
async def activate_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.activate_user(user_id, admin)


@router.delete(
    "/users/{user_id}",
    summary="Delete a user",
    description=(
        "Permanently delete a user account and all cascading data: books, borrow requests, "
        "chats, reviews, wishlist. This action is irreversible. "
        "Cannot delete another admin account."
    ),
    responses={
        403: {"description": "Cannot delete another admin"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.delete_user(user_id, admin)


# ═══════════════════════════════════════════════════════════
# BOOK MANAGEMENT
# ═══════════════════════════════════════════════════════════

@router.get(
    "/books",
    response_model=AdminBookListResponse,
    summary="List all book listings",
    description=(
        "Paginated list of all books on the platform with optional filters: "
        "`search` (title/author), `availability` (available/borrowed/unavailable), `genre_id`. "
        "Includes owner info (name, email) and avg rating."
    ),
)
async def list_books(
    search: Optional[str] = Query(None, description="Search by title or author"),
    availability: Optional[str] = Query(None, description="Filter by availability: available | borrowed | unavailable"),
    genre_id: Optional[int] = Query(None, description="Filter by genre ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.list_books(search, availability, genre_id, page, size)


@router.patch(
    "/books/{book_id}",
    response_model=AdminBookActionResponse,
    summary="Update a book listing",
    description=(
        "Admin override to update a book's availability status or description. "
        "Example: set `availability='unavailable'` to hide a listing that violates platform policies. "
        "The book owner receives an FCM push + email notification when marked unavailable."
    ),
    responses={404: {"description": "Book not found"}},
)
async def update_book(
    book_id: int,
    data: AdminBookUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.update_book(book_id, data)


@router.delete(
    "/books/{book_id}",
    response_model=AdminBookActionResponse,
    summary="Remove a book listing",
    description=(
        "Permanently delete a book listing and all related data "
        "(borrow requests, reviews, wishlist entries). "
        "Use when a listing is inaccurate, inappropriate, or violates platform policies. "
        "The book owner receives an FCM push + email notification."
    ),
    responses={404: {"description": "Book not found"}},
)
async def delete_book(
    book_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.delete_book(book_id)


# ═══════════════════════════════════════════════════════════
# REVIEWS & RATINGS MONITORING
# ═══════════════════════════════════════════════════════════

@router.get(
    "/reviews",
    response_model=AdminReviewListResponse,
    summary="List all reviews",
    description=(
        "Paginated list of all community reviews on the platform. "
        "Filter by `book_id` to see reviews for a specific book, "
        "or use `min_rating` / `max_rating` to find suspiciously low or high reviews. "
        "Includes reviewer and reviewee names, rating, and review text."
    ),
)
async def list_reviews(
    book_id: Optional[int] = Query(None, description="Filter by book ID"),
    min_rating: Optional[float] = Query(None, ge=1.0, le=5.0, description="Minimum rating filter"),
    max_rating: Optional[float] = Query(None, ge=1.0, le=5.0, description="Maximum rating filter"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.list_reviews(book_id, min_rating, max_rating, page, size)


@router.delete(
    "/reviews/{review_id}",
    response_model=AdminReviewActionResponse,
    summary="Delete a review",
    description=(
        "Permanently remove an abusive, fraudulent, or policy-violating review. "
        "Automatically recalculates the affected book's `avg_rating` "
        "and the reviewee user's `avg_rating` to maintain fairness."
    ),
    responses={404: {"description": "Review not found"}},
)
async def delete_review(
    review_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.delete_review(review_id)


# ═══════════════════════════════════════════════════════════
# NOTIFICATIONS MANAGEMENT
# ═══════════════════════════════════════════════════════════

@router.post(
    "/notifications/broadcast",
    response_model=AdminBroadcastNotificationResponse,
    summary="Broadcast notification",
    description=(
        "Send a push notification (FCM) and/or email to all active users or a specific user. "
        "Use `target='all'` for platform-wide announcements (maintenance windows, new features). "
        "Use `target='user'` with `user_id` for targeted messages (borrow reminders, policy warnings). "
        "Push and email are dispatched via Celery background tasks — the response is immediate."
    ),
    responses={
        404: {"description": "User not found (when target='user')"},
        422: {"description": "user_id required when target='user'"},
    },
)
async def broadcast_notification(
    data: AdminBroadcastNotificationRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = AdminManagementService(db)
    return service.broadcast_notification(data)
