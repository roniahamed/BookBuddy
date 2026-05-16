"""
Borrowing module Pydantic schemas.

Covers: Borrowed tab (countdown, Mark as Returned), Lent Out tab (countdown, Confirm Received).
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Embedded Book Info ──────────────────────────────────
class BorrowBookBrief(BaseModel):
    """Brief book info shown on Borrowed/Lent Out cards."""
    id: int
    title: str
    author_name: str
    front_cover_url: Optional[str] = None
    description: Optional[str] = None
    avg_rating: float = 0.0

    model_config = {"from_attributes": True}


class BorrowUserBrief(BaseModel):
    """Brief user info for borrower/owner display."""
    id: int
    full_name: str
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Borrow Request Response ────────────────────────────
class BorrowRequestResponse(BaseModel):
    """
    Single borrow request with computed time_remaining.
    Powers the "Return in 5 days 12 Hours" countdown on UI.
    """
    id: int
    status: str
    requested_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    borrowed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    # Computed fields
    time_remaining: Optional[str] = None  # "5 days 12 Hours" or "Overdue"
    # Related entities
    book: Optional[BorrowBookBrief] = None
    borrower: Optional[BorrowUserBrief] = None

    model_config = {"from_attributes": True}


class BorrowRequestCreateRequest(BaseModel):
    """Request to borrow a book (REQUEST BOOK button)."""
    book_id: int = Field(..., description="ID of the book to borrow")

    model_config = {"json_schema_extra": {
        "example": {"book_id": 1}
    }}


class BorrowRequestCreateResponse(BaseModel):
    """Response after creating a borrow request."""
    id: int
    status: str = "pending"
    message: str = "Borrow request submitted successfully"


# ─── Paginated Response ──────────────────────────────────
class BorrowRequestPaginatedResponse(BaseModel):
    """Paginated list for Borrowed / Lent Out tabs."""
    items: List[BorrowRequestResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False


# ─── Status Update Responses ────────────────────────────
class BorrowStatusUpdateResponse(BaseModel):
    """Generic response for status transition actions."""
    id: int
    status: str
    message: str
