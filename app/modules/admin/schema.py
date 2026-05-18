"""
Admin module schemas — covers:
- AppConfig CRUD (existing)
- User Management
- Book Management
- Reviews & Ratings Monitoring
- Notifications Broadcast
- Platform Stats
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ─── AppConfig (existing) ─────────────────────────────────

class AppConfigResponse(BaseModel):
    """Single config entry."""
    id: int
    key: str
    value: str
    description: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AppConfigUpdateRequest(BaseModel):
    """Update a config value."""
    value: str = Field(..., description="New value for this config")

    model_config = {"json_schema_extra": {
        "example": {"value": "15"}
    }}


class AppConfigListResponse(BaseModel):
    """List of all configs."""
    items: List[AppConfigResponse] = []


# ─── Platform Stats ───────────────────────────────────────

class AdminStatsResponse(BaseModel):
    """Dashboard overview counts for the admin panel."""
    total_users: int = 0
    active_users: int = 0
    suspended_users: int = 0
    total_books: int = 0
    available_books: int = 0
    borrowed_books: int = 0
    total_borrow_requests: int = 0
    pending_borrow_requests: int = 0
    active_borrow_requests: int = 0
    overdue_borrow_requests: int = 0
    total_reviews: int = 0
    avg_platform_rating: float = 0.0


# ─── User Management ──────────────────────────────────────

class AdminUserListItem(BaseModel):
    """One row in the admin user list."""
    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    credits: int = 0
    avg_rating: float = 0.0
    books_uploaded: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminUserDetailResponse(BaseModel):
    """Full user detail for admin — includes all fields."""
    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    credits: int = 0
    avg_rating: float = 0.0
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    auth_provider: str = "email"
    firebase_uid: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Computed stats
    books_uploaded: int = 0
    books_available: int = 0
    books_borrowed: int = 0
    reviews_written: int = 0
    reviews_received: int = 0

    model_config = {"from_attributes": True}


class AdminUserSuspendRequest(BaseModel):
    """Optional reason when suspending a user."""
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional reason for suspension (for audit logs / notifications)",
    )

    model_config = {"json_schema_extra": {
        "example": {"reason": "Repeatedly failed to return books on time."}
    }}


class AdminUserActionResponse(BaseModel):
    """Generic response after a user management action."""
    message: str
    user_id: int
    is_active: bool


class AdminUserListResponse(BaseModel):
    """Paginated user list."""
    items: List[AdminUserListItem] = []
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 1


# ─── Book Management ──────────────────────────────────────

class AdminBookListItem(BaseModel):
    """One row in the admin book list."""
    id: int
    title: str
    author_name: str
    owner_id: int
    owner_name: str = ""
    owner_email: str = ""
    genre_name: Optional[str] = None
    availability: str
    condition: str
    avg_rating: float = 0.0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminBookUpdateRequest(BaseModel):
    """Admin override for a book listing."""
    availability: Optional[Literal["available", "borrowed", "unavailable"]] = Field(
        None, description="Override book availability status"
    )
    description: Optional[str] = Field(None, description="Update book description")

    model_config = {"json_schema_extra": {
        "example": {"availability": "unavailable", "description": "Removed: Policy violation."}
    }}


class AdminBookActionResponse(BaseModel):
    """Generic response after a book management action."""
    message: str
    book_id: int


class AdminBookListResponse(BaseModel):
    """Paginated book list."""
    items: List[AdminBookListItem] = []
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 1


# ─── Reviews & Ratings Monitoring ─────────────────────────

class AdminReviewListItem(BaseModel):
    """One row in the admin review list."""
    id: int
    book_id: int
    book_title: str = ""
    reviewer_id: int
    reviewer_name: str = ""
    reviewee_id: int
    reviewee_name: str = ""
    rating: float
    review_text: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminReviewActionResponse(BaseModel):
    """Generic response after a review management action."""
    message: str
    review_id: int


class AdminReviewListResponse(BaseModel):
    """Paginated review list."""
    items: List[AdminReviewListItem] = []
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 1


# ─── Notifications Broadcast ──────────────────────────────

class AdminBroadcastNotificationRequest(BaseModel):
    """Payload for broadcasting a push + email notification."""
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    body: str = Field(..., min_length=1, description="Notification message body")
    target: Literal["all", "user"] = Field(
        "all",
        description="'all' = every active user, 'user' = single user by user_id",
    )
    user_id: Optional[int] = Field(
        None,
        description="Required when target='user'. The specific user to notify.",
    )
    send_email: bool = Field(True, description="Also send an email notification")
    send_push: bool = Field(True, description="Also send an FCM push notification")

    model_config = {"json_schema_extra": {
        "example": {
            "title": "Platform Maintenance",
            "body": "BookBuddy will be down for maintenance on Sunday from 2–4 AM UTC.",
            "target": "all",
            "send_email": True,
            "send_push": True,
        }
    }}


class AdminBroadcastNotificationResponse(BaseModel):
    """Result after a broadcast."""
    message: str
    recipients_count: int
    push_sent: bool = False
    email_sent: bool = False
