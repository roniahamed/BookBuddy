"""
Books module API endpoints.

Covers:
- GET    /books                — Browse books (search, filter, sort, paginate)
- GET    /books/nearby         — Books Near You
- GET    /books/recommended    — Recommended for You
- GET    /books/new-arrivals   — New Arrivals
- GET    /books/top-rated      — Top Rated
- GET    /books/my-books       — My uploaded books
- GET    /books/{id}           — Book detail page
- POST   /books               — Upload new book
- PATCH  /books/{id}           — Update book (owner only)
- DELETE /books/{id}           — Delete book (owner only)
- GET    /genres               — List all genres
- POST   /books/{id}/wishlist  — Add to wishlist
- DELETE /books/{id}/wishlist  — Remove from wishlist
- GET    /books/wishlist       — My wishlist
- POST   /reviews              — Submit review
- GET    /books/{id}/reviews   — Book reviews
- GET    /users/{id}/reviews   — User community ratings
"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.dependencies import get_db
from app.modules.auth.dependencies import get_current_user, get_current_user_optional
from app.modules.users.model import User
from app.modules.books.service import BookService
from app.modules.books.filters import BookFilters
from app.modules.books.schema import (
    BookListItemResponse, BookDetailResponse,
    BookCreateRequest, BookUpdateRequest,
    BookPaginatedResponse, GenreResponse,
    ReviewCreateRequest, ReviewResponse, ReviewPaginatedResponse,
)
from app.shared.pagination import PaginationParams

router = APIRouter()
review_router = APIRouter()
genre_router = APIRouter()


# ─── Browse & Discovery ─────────────────────────────────

@router.get(
    "",
    response_model=BookPaginatedResponse,
    summary="Browse community books",
    description=(
        "Browse and search books with powerful filtering options. "
        "Supports text search (title, author, genre), genre category filter, "
        "condition filter (New/Good/Used), availability filter, and proximity sort. "
        "Results are paginated. Authentication is optional — authenticated users "
        "get `is_wishlisted` info on each book."
    ),
)
async def browse_books(
    filters: BookFilters = Depends(),
    pagination: PaginationParams = Depends(),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.browse_books(filters, pagination, current_user)


@router.get(
    "/nearby",
    response_model=BookPaginatedResponse,
    summary="Books Near You",
    description=(
        "Get available books near the authenticated user's location, sorted by distance. "
        "Requires the user to have GPS coordinates set in their profile. "
        "Uses Haversine formula for accurate distance calculation."
    ),
    responses={400: {"description": "User location not set"}},
)
async def get_nearby_books(
    radius_km: float = Query(50, ge=1, le=500, description="Search radius in km"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_nearby_books(current_user, pagination, radius_km)


@router.get(
    "/recommended",
    response_model=List[BookListItemResponse],
    summary="Recommended for you",
    description=(
        "Get personalized book recommendations based on the user's borrowing history. "
        "Analyzes genres from previously borrowed books and suggests available books in similar genres. "
        "Falls back to top-rated available books if no borrowing history exists."
    ),
)
async def get_recommended_books(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_recommended_books(current_user)


@router.get(
    "/new-arrivals",
    response_model=BookPaginatedResponse,
    summary="New arrivals",
    description="Get most recently added available books, sorted by creation date.",
)
async def get_new_arrivals(
    pagination: PaginationParams = Depends(),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_new_arrivals(pagination, current_user)


@router.get(
    "/top-rated",
    response_model=BookPaginatedResponse,
    summary="Top rated books",
    description="Get highest-rated available books based on community ratings.",
)
async def get_top_rated(
    pagination: PaginationParams = Depends(),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_top_rated(pagination, current_user)


# ─── My Books & Wishlist ─────────────────────────────────

@router.get(
    "/my-books",
    response_model=BookPaginatedResponse,
    summary="My uploaded books",
    description="Get all books uploaded by the current user (My Book tab on Profile screen).",
)
async def get_my_books(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_my_books(current_user, pagination)


@router.get(
    "/wishlist",
    response_model=BookPaginatedResponse,
    summary="My wishlist",
    description="Get all books in the current user's wishlist (Wishlist tab on Profile screen).",
)
async def get_my_wishlist(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_my_wishlist(current_user, pagination)


# ─── Single Book ─────────────────────────────────────────

@router.get(
    "/{book_id}",
    response_model=BookDetailResponse,
    summary="Book detail page",
    description=(
        "Get full details for a single book including owner info, genre, "
        "rating, borrow duration, and review count. "
        "Authenticated users also get `is_wishlisted` status and distance."
    ),
    responses={404: {"description": "Book not found"}},
)
async def get_book_detail(
    book_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_book_detail(book_id, current_user)


@router.post(
    "",
    response_model=BookDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new book",
    description=(
        "List a new book for community sharing (Upload Book modal). "
        "Provide title, author, genre, condition, cover images, location, "
        "and borrow duration. The book will be set as 'available' by default."
    ),
)
async def create_book(
    data: BookCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.create_book(current_user, data)


@router.patch(
    "/{book_id}",
    response_model=BookDetailResponse,
    summary="Update book details",
    description="Update book information. Only the book owner can edit their books.",
    responses={
        403: {"description": "Not the book owner"},
        404: {"description": "Book not found"},
    },
)
async def update_book(
    book_id: int,
    data: BookUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.update_book(book_id, current_user, data)


@router.delete(
    "/{book_id}",
    summary="Delete a book",
    description="Permanently delete a book listing and all related data. Only the book owner can delete their books.",
    responses={
        403: {"description": "Not the book owner"},
        404: {"description": "Book not found"},
    },
)
async def delete_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.delete_book(book_id, current_user)


# ─── Wishlist Actions ────────────────────────────────────

@router.post(
    "/{book_id}/wishlist",
    status_code=status.HTTP_201_CREATED,
    summary="Add book to wishlist",
    description="Save a book to your wishlist (heart icon on book cards).",
    responses={
        404: {"description": "Book not found"},
        409: {"description": "Book already in wishlist"},
    },
)
async def add_to_wishlist(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.add_to_wishlist(current_user, book_id)


@router.delete(
    "/{book_id}/wishlist",
    summary="Remove book from wishlist",
    description="Remove a book from your wishlist.",
    responses={404: {"description": "Book not in wishlist"}},
)
async def remove_from_wishlist(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.remove_from_wishlist(current_user, book_id)


# ─── Book Reviews ────────────────────────────────────────

@router.get(
    "/{book_id}/reviews",
    response_model=ReviewPaginatedResponse,
    summary="Get book reviews",
    description=(
        "Get community ratings/reviews for a specific book. "
        "Shown in the 'Community Ratings' section on the Book Details page."
    ),
)
async def get_book_reviews(
    book_id: int,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_book_reviews(book_id, pagination)


@router.get(
    "/{book_id}/translate",
    summary="Translate book details",
    description=(
        "Auto-translate book details (title, description, author) to the target language. "
        "Supports EN ↔ HE (English ↔ Hebrew) auto-detection. "
        "Translation results are cached in Redis for 24 hours."
    ),
    responses={404: {"description": "Book not found"}},
)
async def translate_book(
    book_id: int,
    lang: str = Query("HE", description="Target language code (EN or HE)"),
    db: Session = Depends(get_db),
):
    from app.core.translation import translate_book_fields
    import redis
    from app.core.config import settings

    service = BookService(db)
    book = service.repo.get_book_by_id(book_id)
    if not book:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Book not found")

    target_lang = lang.lower()

    # Check Redis cache first
    cache_key = f"translate:{book_id}:{target_lang}"
    try:
        r = redis.from_url(settings.REDIS_URL)
        cached = r.get(cache_key)
        if cached:
            import json
            return json.loads(cached)
    except Exception:
        pass  # Redis not available, proceed without cache

    # Translate
    result = translate_book_fields(
        title=book.title,
        description=book.description,
        author_name=book.author_name,
        target_lang=target_lang,
    )
    result["book_id"] = book_id
    result["original_title"] = book.title

    # Cache in Redis
    try:
        import json
        r = redis.from_url(settings.REDIS_URL)
        r.setex(cache_key, 86400, json.dumps(result))
    except Exception:
        pass

    return result


# ─── Reviews Router ──────────────────────────────────────

@review_router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a review",
    description=(
        "Submit a community rating for a completed borrow transaction. "
        "Borrowers can review lenders, and lenders can review borrowers. "
        "Each user can only submit one review per transaction. "
        "Automatically updates the reviewee's and book's average rating."
    ),
    responses={
        400: {"description": "Borrow not yet returned"},
        403: {"description": "Not part of this transaction"},
        404: {"description": "Borrow request not found"},
        409: {"description": "Already reviewed"},
    },
)
async def submit_review(
    data: ReviewCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.submit_review(current_user, data)


# ─── Genres Router ───────────────────────────────────────

@genre_router.get(
    "",
    response_model=List[GenreResponse],
    summary="List all genres",
    description=(
        "Get all available book genres for the category filter tabs. "
        "Genres: Science, History, Self-Help, Fiction, Children's, Business, Drama, Fantasy."
    ),
)
async def list_genres(db: Session = Depends(get_db)):
    service = BookService(db)
    return service.get_all_genres()
