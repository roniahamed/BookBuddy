"""
Contact module Pydantic schemas.
Covers: Contact Us form submission, list view, single view.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ─── Submitter brief (embedded in response) ───────────────
class ContactUserBrief(BaseModel):
    """Submitting user info if logged in."""
    id: int
    full_name: str
    email: str

    model_config = {"from_attributes": True}


# ─── Contact Response ─────────────────────────────────────
class ContactResponse(BaseModel):
    """Contact form submission as returned by GET endpoints."""
    id: int
    name: str
    email: str
    subject: str
    message: str
    status: str = "open"
    user: Optional[ContactUserBrief] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Contact Create ───────────────────────────────────────
class ContactCreateRequest(BaseModel):
    """Contact Us form fields (POST /contact)."""
    name: str = Field(..., min_length=2, max_length=150, description="Your full name")
    email: EmailStr = Field(..., description="Your email address for reply")
    subject: str = Field(..., min_length=3, max_length=255, description="Message subject")
    message: str = Field(..., min_length=10, description="Your message")

    model_config = {"json_schema_extra": {
        "example": {
            "name": "Alex Morgan",
            "email": "alex@example.com",
            "subject": "Issue with book borrowing",
            "message": "I tried to request a book but keep getting an error. Please help!",
        }
    }}


# ─── Paginated Contact Response ───────────────────────────
class ContactPaginatedResponse(BaseModel):
    """Paginated list of contact submissions."""
    items: List[ContactResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False
