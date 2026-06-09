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
from fastapi import APIRouter, Depends, status, Query, File, UploadFile, Request, Form
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
    BookPaginatedResponse, GenreResponse, GenreCreate, AuthorResponse, AuthorCreate,
    ReviewCreateRequest, ReviewResponse, ReviewPaginatedResponse,
    GenrePaginatedResponse, AuthorPaginatedResponse, ExternalBookSearchResponse
)
from app.shared.pagination import PaginationParams

router = APIRouter()
review_router = APIRouter()
genre_router = APIRouter()
author_router = APIRouter()


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
    response_model=BookPaginatedResponse,
    summary="Recommended for you",
    description=(
        "Get personalized book recommendations based on the user's borrowing history. "
        "Analyzes genres from previously borrowed books and suggests available books in similar genres. "
        "Falls back to top-rated available books if no borrowing history exists."
    ),
)
async def get_recommended_books(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_recommended_books(current_user, pagination)


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
    "/search-external",
    response_model=ExternalBookSearchResponse,
    summary="Search books from external API",
    description=(
        "Search for books via Google Books API (by title, author, or ISBN) "
        "to auto-fill frontend forms. Returns a list of matches including "
        "front_cover_image and back_cover_image (if available)."
    ),
)
async def search_external_books(
    q: str = Query(..., description="Search query (title, author, or ISBN)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.search_external_books(q)



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
    request: Request,
    title: str = Form(..., min_length=1, max_length=255, description="Book title"),
    author_id: Optional[int] = Form(None, description="Author ID from /authors"),
    author_name: Optional[str] = Form(None, description="Author name if new"),
    genre_id: Optional[int] = Form(None, description="Genre ID from /genres"),
    genre_name: Optional[str] = Form(None, description="Genre name if new"),
    description: Optional[str] = Form(None, description="Book description and condition"),
    language: Optional[str] = Form("English", description="Book language"),
    condition: str = Form("Good", description="Book condition: New | Good | Used"),
    borrow_duration_days: int = Form(30, ge=1, le=365, description="Max borrow days"),
    location: Optional[str] = Form(None, max_length=255, description="Pickup address"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    front_cover_image: Optional[UploadFile] = File(None, description="Front cover image file"),
    back_cover_image: Optional[UploadFile] = File(None, description="Back cover image file"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import uuid
    import shutil
    import os

    def save_upload(file: UploadFile):
        if not file or not file.filename:
            return None
        upload_dir = "static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        base_url = str(request.base_url).rstrip("/")
        return f"{base_url}/static/uploads/{unique_filename}"

    front_cover_url = save_upload(front_cover_image)
    back_cover_url = save_upload(back_cover_image)

    data = BookCreateRequest(
        title=title,
        author_id=author_id,
        author_name=author_name,
        genre_id=genre_id,
        genre_name=genre_name,
        description=description,
        language=language,
        front_cover_image=front_cover_url,
        back_cover_image=back_cover_url,
        condition=condition,
        borrow_duration_days=borrow_duration_days,
        location=location,
        latitude=latitude,
        longitude=longitude
    )
    service = BookService(db)
    return service.create_book(current_user, data)


@router.post(
    "/upload-image",
    summary="Upload cover image directly",
    description="Upload an image file directly (front or back cover) and get a public static URL.",
)
async def upload_book_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    import uuid
    import shutil
    import os

    # Ensure directories exist
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename preserving extension
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Build full URL
    base_url = str(request.base_url).rstrip("/")
    file_url = f"{base_url}/static/uploads/{unique_filename}"

    return {"url": file_url}


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
        author_name=book.author.name if book.author else "",
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


# ─── Reviews Router ──────────────────────────────────────────

@review_router.get(
    "",
    response_model=ReviewPaginatedResponse,
    summary="List all reviews",
    description=(
        "Get all community reviews across all users and books, ordered by newest first. "
        "Optionally filter by `book_id` to get reviews for a specific book."
    ),
)
async def list_all_reviews(
    book_id: Optional[int] = Query(None, description="Filter by book ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_all_reviews(pagination, book_id, user_id)


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


# ─── Genres Router ──────────────────────────────────────────

@genre_router.get(
    "",
    response_model=GenrePaginatedResponse,
    summary="List all genres (categories)",
    description=(
        "Get all available book genres/categories with optional search and sorting. "
        "Supports search by name and sorting (name_asc | name_desc)."
    ),
)
async def list_genres(
    search: Optional[str] = Query(None, description="Search by genre name"),
    sort_by: Optional[str] = Query("name_asc", description="Sort: name_asc | name_desc"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_genres_filtered(search, sort_by, pagination)


@genre_router.post(
    "",
    response_model=GenreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category (genre)",
)
async def create_genre(
    data: GenreCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BookService(db)
    return service.create_genre(data)


# ─── Authors Router ──────────────────────────────────────────

@author_router.get(
    "",
    response_model=AuthorPaginatedResponse,
    summary="List all authors",
    description=(
        "Get all authors with optional search by name and sorting. "
        "Supports search by name and sorting (name_asc | name_desc)."
    ),
)
async def list_authors(
    search: Optional[str] = Query(None, description="Search by author name"),
    sort_by: Optional[str] = Query("name_asc", description="Sort: name_asc | name_desc"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_authors_filtered(search, sort_by, pagination)


@author_router.post(
    "",
    response_model=AuthorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an author",
)
async def create_author(
    data: AuthorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BookService(db)
    return service.create_author(data)
