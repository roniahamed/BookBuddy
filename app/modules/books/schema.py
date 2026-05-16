"""
Books module Pydantic schemas.

Covers: Home page cards, Browse Book, Book Details, Upload Book, Wishlist, Reviews.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Genre ───────────────────────────────────────────────
class GenreResponse(BaseModel):
    """Genre item for the category filter tabs."""
    id: int
    name: str

    model_config = {"from_attributes": True}


# ─── Book Owner (embedded) ───────────────────────────────
class BookOwnerBrief(BaseModel):
    """Brief owner info shown on book cards and detail pages."""
    id: int
    full_name: str
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    avg_rating: float = 0.0

    model_config = {"from_attributes": True}


# ─── Book Response (list view — card) ────────────────────
class BookListItemResponse(BaseModel):
    """Book card shown on Home page grid, Browse Book, and search results."""
    id: int
    title: str
    author_name: str
    front_cover_url: Optional[str] = None
    back_cover_url: Optional[str] = None
    condition: str
    availability: str
    avg_rating: float = 0.0
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    borrow_duration_days: int = 30
    distance_km: Optional[float] = None  # Computed if user location provided
    genre: Optional[GenreResponse] = None
    owner: Optional[BookOwnerBrief] = None
    is_wishlisted: bool = False  # Whether current user wishlisted this
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Book Detail Response ────────────────────────────────
class BookDetailResponse(BaseModel):
    """Full book detail page — includes description, reviews, recommendations."""
    id: int
    title: str
    author_name: str
    description: Optional[str] = None
    front_cover_url: Optional[str] = None
    back_cover_url: Optional[str] = None
    condition: str
    availability: str
    avg_rating: float = 0.0
    borrow_duration_days: int = 30
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    genre: Optional[GenreResponse] = None
    owner: Optional[BookOwnerBrief] = None
    is_wishlisted: bool = False
    reviews_count: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Book Create (Upload) ───────────────────────────────
class BookCreateRequest(BaseModel):
    """Upload Book modal form fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Book title")
    author_name: str = Field(..., min_length=1, max_length=255, description="Author name")
    genre_id: Optional[int] = Field(None, description="Genre ID from /genres")
    description: Optional[str] = Field(None, description="Book description and condition")
    front_cover_url: Optional[str] = Field(None, max_length=500, description="Front cover image URL")
    back_cover_url: Optional[str] = Field(None, max_length=500, description="Back cover image URL")
    condition: str = Field("Good", description="Book condition: New | Good | Used")
    borrow_duration_days: int = Field(30, ge=1, le=365, description="Max borrow days")
    location: Optional[str] = Field(None, max_length=255, description="Pickup address")
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"json_schema_extra": {
        "example": {
            "title": "A Tale of Love and Darkness",
            "author_name": "Amos Oz",
            "genre_id": 1,
            "description": "A deeply personal memoir exploring family, memory, and the birth of Israel.",
            "condition": "Good",
            "borrow_duration_days": 30,
            "location": "Westheimer Rd. Santa Ana, Illinois",
            "latitude": 33.7455,
            "longitude": -117.8677,
        }
    }}


class BookUpdateRequest(BaseModel):
    """Update book details (owner only)."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author_name: Optional[str] = Field(None, min_length=1, max_length=255)
    genre_id: Optional[int] = None
    description: Optional[str] = None
    front_cover_url: Optional[str] = None
    back_cover_url: Optional[str] = None
    condition: Optional[str] = None
    borrow_duration_days: Optional[int] = Field(None, ge=1, le=365)
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    availability: Optional[str] = None


# ─── Paginated Book Response ─────────────────────────────
class BookPaginatedResponse(BaseModel):
    """Paginated list of books for Browse Book screen."""
    items: List[BookListItemResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False


# ─── Review ──────────────────────────────────────────────
class ReviewerBrief(BaseModel):
    """Reviewer info shown in Community Ratings section."""
    id: int
    full_name: str
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    avg_rating: float = 0.0

    model_config = {"from_attributes": True}


class ReviewResponse(BaseModel):
    """Single review in the Community Ratings section."""
    id: int
    rating: float
    review_text: Optional[str] = None
    created_at: Optional[datetime] = None
    reviewer: Optional[ReviewerBrief] = None
    book_title: Optional[str] = None

    model_config = {"from_attributes": True}


class ReviewCreateRequest(BaseModel):
    """Submit a review for a completed borrow transaction."""
    borrow_request_id: int = Field(..., description="ID of the completed borrow request")
    rating: float = Field(..., ge=0, le=5, description="Star rating (0-5)")
    review_text: Optional[str] = Field(None, description="Written review text")

    model_config = {"json_schema_extra": {
        "example": {
            "borrow_request_id": 1,
            "rating": 4.8,
            "review_text": "I recently borrowed a book from this platform, and it was an amazing experience.",
        }
    }}


class ReviewPaginatedResponse(BaseModel):
    """Paginated reviews for Community Ratings."""
    items: List[ReviewResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False


# ─── Wishlist ────────────────────────────────────────────
class WishlistItemResponse(BaseModel):
    """Wishlist item with book details."""
    id: int
    book: BookListItemResponse
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WishlistPaginatedResponse(BaseModel):
    """Paginated wishlist."""
    items: List[WishlistItemResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False
