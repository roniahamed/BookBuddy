"""
Books module service — business logic for books, wishlist, and reviews.
"""
import math
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.modules.books.repository import BookRepository
from app.modules.books.filters import BookFilters
from app.modules.books.model import Book
from app.modules.books.schema import (
    BookListItemResponse, BookDetailResponse, BookCreateRequest, BookUpdateRequest,
    BookPaginatedResponse, BookOwnerBrief, GenreResponse, GenreCreate, AuthorResponse, AuthorCreate,
    ReviewCreateRequest, ReviewResponse, ReviewerBrief, ReviewPaginatedResponse,
    WishlistItemResponse, WishlistPaginatedResponse,
)
from app.modules.users.model import User
from app.shared.pagination import PaginationParams


def _calc_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Haversine distance in km (Python fallback for single items)."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _book_to_list_item(
    book: Book,
    user_lat: float = None,
    user_lon: float = None,
    wishlisted_ids: set = None,
) -> BookListItemResponse:
    """Convert Book model to list item response with computed fields."""
    distance = None
    if user_lat and user_lon and book.latitude and book.longitude:
        distance = round(_calc_distance(user_lat, user_lon, book.latitude, book.longitude), 1)

    genre = GenreResponse.model_validate(book.genre) if book.genre else None
    author = AuthorResponse.model_validate(book.author) if book.author else None
    owner = BookOwnerBrief.model_validate(book.owner) if book.owner else None
    is_wishlisted = book.id in wishlisted_ids if wishlisted_ids else False

    return BookListItemResponse(
        id=book.id,
        title=book.title,
        author=author,
        front_cover_url=book.front_cover_url,
        back_cover_url=book.back_cover_url,
        condition=book.condition,
        availability=book.availability,
        avg_rating=book.avg_rating or 0.0,
        location=book.location,
        latitude=book.latitude,
        longitude=book.longitude,
        borrow_duration_days=book.borrow_duration_days,
        distance_km=distance,
        genre=genre,
        owner=owner,
        is_wishlisted=is_wishlisted,
        created_at=book.created_at,
    )


class BookService:
    """Handles book-related business logic."""

    def __init__(self, db: Session):
        self.repo = BookRepository(db)

    def browse_books(
        self,
        filters: BookFilters,
        pagination: PaginationParams,
        current_user: Optional[User] = None,
    ) -> BookPaginatedResponse:
        """Browse books with search, filter, sort, pagination (Browse Book screen)."""
        books, total = self.repo.get_books_filtered(
            filters=filters,
            offset=pagination.offset,
            limit=pagination.per_page,
            user_id=current_user.id if current_user else None,
        )

        # Batch fetch wishlisted IDs if user is authenticated
        wishlisted_ids = set()
        if current_user:
            wishlisted_ids = self.repo.get_user_wishlisted_book_ids(current_user.id)

        items = [
            _book_to_list_item(b, filters.user_lat, filters.user_lon, wishlisted_ids)
            for b in books
        ]

        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BookPaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            pages=pages,
            has_next=pagination.page < pages,
            has_prev=pagination.page > 1,
        )

    def get_nearby_books(
        self,
        user: User,
        pagination: PaginationParams,
        radius_km: float = 50,
    ) -> BookPaginatedResponse:
        """Books Near You section on Home page."""
        if not user.latitude or not user.longitude:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Location not set. Please update your profile with GPS coordinates.",
            )

        books, total = self.repo.get_nearby_books(
            lat=user.latitude,
            lon=user.longitude,
            radius_km=radius_km,
            offset=pagination.offset,
            limit=pagination.per_page,
        )

        wishlisted_ids = self.repo.get_user_wishlisted_book_ids(user.id)
        items = [
            _book_to_list_item(b, user.latitude, user.longitude, wishlisted_ids)
            for b in books
        ]

        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BookPaginatedResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def get_recommended_books(self, user: User, pagination: PaginationParams) -> BookPaginatedResponse:
        """Recommended for you section on Home page."""
        books, total = self.repo.get_recommended_books(user.id, offset=pagination.offset, limit=pagination.per_page)
        wishlisted_ids = self.repo.get_user_wishlisted_book_ids(user.id)
        items = [
            _book_to_list_item(
                b,
                user.latitude, user.longitude,
                wishlisted_ids,
            )
            for b in books
        ]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BookPaginatedResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def get_new_arrivals(self, pagination: PaginationParams, current_user: User = None) -> BookPaginatedResponse:
        """New Arrivals filter."""
        books, total = self.repo.get_new_arrivals(limit=pagination.per_page, offset=pagination.offset)
        wishlisted_ids = self.repo.get_user_wishlisted_book_ids(current_user.id) if current_user else set()
        items = [_book_to_list_item(b, wishlisted_ids=wishlisted_ids) for b in books]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BookPaginatedResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def get_top_rated(self, pagination: PaginationParams, current_user: User = None) -> BookPaginatedResponse:
        """Top Rated filter."""
        books, total = self.repo.get_top_rated(limit=pagination.per_page, offset=pagination.offset)
        wishlisted_ids = self.repo.get_user_wishlisted_book_ids(current_user.id) if current_user else set()
        items = [_book_to_list_item(b, wishlisted_ids=wishlisted_ids) for b in books]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BookPaginatedResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def get_book_detail(self, book_id: int, current_user: User = None) -> BookDetailResponse:
        """Full book detail page."""
        book = self.repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        genre = GenreResponse.model_validate(book.genre) if book.genre else None
        author = AuthorResponse.model_validate(book.author) if book.author else None
        owner = BookOwnerBrief.model_validate(book.owner) if book.owner else None
        reviews_count = self.repo.get_reviews_count_for_book(book_id)

        is_wishlisted = False
        distance_km = None
        if current_user:
            is_wishlisted = self.repo.is_wishlisted(current_user.id, book_id)
            if current_user.latitude and current_user.longitude and book.latitude and book.longitude:
                distance_km = round(
                    _calc_distance(current_user.latitude, current_user.longitude, book.latitude, book.longitude), 1
                )

        return BookDetailResponse(
            id=book.id,
            title=book.title,
            author=author,
            description=book.description,
            front_cover_url=book.front_cover_url,
            back_cover_url=book.back_cover_url,
            condition=book.condition,
            availability=book.availability,
            avg_rating=book.avg_rating or 0.0,
            borrow_duration_days=book.borrow_duration_days,
            location=book.location,
            latitude=book.latitude,
            longitude=book.longitude,
            distance_km=distance_km,
            genre=genre,
            owner=owner,
            is_wishlisted=is_wishlisted,
            reviews_count=reviews_count,
            created_at=book.created_at,
        )

    def create_book(self, user: User, data: BookCreateRequest) -> BookDetailResponse:
        """Upload new book (Upload Book modal)."""
        book_data = data.model_dump(exclude_unset=True)
        book = self.repo.create_book(owner_id=user.id, data=book_data)
        return self.get_book_detail(book.id, user)

    def update_book(self, book_id: int, user: User, data: BookUpdateRequest) -> BookDetailResponse:
        """Update book details (owner only)."""
        book = self.repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.owner_id != user.id:
            raise HTTPException(status_code=403, detail="You can only edit your own books")

        update_data = data.model_dump(exclude_unset=True)
        self.repo.update_book(book_id, update_data)
        return self.get_book_detail(book_id, user)

    def delete_book(self, book_id: int, user: User) -> dict:
        """HARD DELETE book (owner only). Permanently removes the book and all related data."""
        book = self.repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book.owner_id != user.id:
            raise HTTPException(status_code=403, detail="You can only delete your own books")

        self.repo.hard_delete_book(book_id)
        return {"message": "Book permanently deleted"}

    def get_my_books(self, user: User, pagination: PaginationParams) -> BookPaginatedResponse:
        """My Book tab on Profile screen."""
        books, total = self.repo.get_books_by_owner(user.id, pagination.offset, pagination.per_page)
        items = [_book_to_list_item(b) for b in books]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BookPaginatedResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def get_user_books(self, user_id: int, pagination: PaginationParams) -> BookPaginatedResponse:
        """All Books tab on Other People Profile."""
        books, total = self.repo.get_books_by_owner(user_id, pagination.offset, pagination.per_page)
        items = [_book_to_list_item(b) for b in books]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BookPaginatedResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    # ─── Genres ──────────────────────────────────────────
    def get_all_genres(self) -> list[GenreResponse]:
        """List all genres for category tabs."""
        genres = self.repo.get_all_genres()
        return [GenreResponse.model_validate(g) for g in genres]

    def create_genre(self, data: GenreCreate) -> GenreResponse:
        genre = self.repo.get_or_create_genre(data.name)
        return GenreResponse.model_validate(genre)

    # ─── Authors ─────────────────────────────────────────
    def get_all_authors(self) -> list[AuthorResponse]:
        authors = self.repo.get_all_authors()
        return [AuthorResponse.model_validate(a) for a in authors]

    def create_author(self, data: AuthorCreate) -> AuthorResponse:
        author = self.repo.get_or_create_author(data.name)
        return AuthorResponse.model_validate(author)

    # ─── Wishlist ────────────────────────────────────────
    def add_to_wishlist(self, user: User, book_id: int) -> dict:
        """Add book to wishlist (heart icon on book card)."""
        book = self.repo.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if self.repo.is_wishlisted(user.id, book_id):
            raise HTTPException(status_code=409, detail="Book already in wishlist")

        self.repo.add_to_wishlist(user.id, book_id)
        return {"message": "Book added to wishlist"}

    def remove_from_wishlist(self, user: User, book_id: int) -> dict:
        """Remove book from wishlist."""
        if not self.repo.is_wishlisted(user.id, book_id):
            raise HTTPException(status_code=404, detail="Book not in wishlist")

        self.repo.remove_from_wishlist(user.id, book_id)
        return {"message": "Book removed from wishlist"}

    def get_my_wishlist(self, user: User, pagination: PaginationParams) -> BookPaginatedResponse:
        """Wishlist tab on Profile screen."""
        items, total = self.repo.get_wishlist(user.id, pagination.offset, pagination.per_page)
        book_items = [
            _book_to_list_item(item.book, wishlisted_ids={item.book_id})
            for item in items
        ]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BookPaginatedResponse(
            items=book_items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    # ─── Reviews ─────────────────────────────────────────
    def submit_review(self, user: User, data: ReviewCreateRequest) -> ReviewResponse:
        """Submit review for a completed borrow transaction."""
        from app.modules.borrowing.model import BorrowRequest

        # Verify borrow request exists and is completed
        db = self.repo.db
        borrow = db.query(BorrowRequest).filter(BorrowRequest.id == data.borrow_request_id).first()
        if not borrow:
            raise HTTPException(status_code=404, detail="Borrow request not found")

        if borrow.status not in ("returned", "confirmed"):
            raise HTTPException(
                status_code=400,
                detail="Can only review after book has been returned"
            )

        # Determine reviewer/reviewee: borrower reviews owner, owner reviews borrower
        book = self.repo.get_book_by_id(borrow.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if user.id == borrow.borrower_id:
            reviewee_id = book.owner_id  # Borrower reviews the lender
        elif user.id == book.owner_id:
            reviewee_id = borrow.borrower_id  # Owner reviews the borrower
        else:
            raise HTTPException(status_code=403, detail="You are not part of this borrow transaction")

        # Check duplicate
        if self.repo.review_exists(data.borrow_request_id, user.id):
            raise HTTPException(status_code=409, detail="You have already reviewed this transaction")

        review = self.repo.create_review({
            "borrow_request_id": data.borrow_request_id,
            "reviewer_id": user.id,
            "reviewee_id": reviewee_id,
            "book_id": borrow.book_id,
            "rating": data.rating,
            "review_text": data.review_text,
        })

        # Update denormalized avg_rating fields
        self.repo.update_book_avg_rating(borrow.book_id)
        self.repo.update_user_avg_rating(reviewee_id)

        return ReviewResponse(
            id=review.id,
            rating=review.rating,
            review_text=review.review_text,
            created_at=review.created_at,
            reviewer=ReviewerBrief(
                id=user.id,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                location=user.location,
                avg_rating=user.avg_rating or 0.0,
            ),
        )

    def get_book_reviews(self, book_id: int, pagination: PaginationParams) -> ReviewPaginatedResponse:
        """Community Ratings section on Book Details page."""
        reviews, total = self.repo.get_reviews_for_book(book_id, pagination.offset, pagination.per_page)
        items = [
            ReviewResponse(
                id=r.id,
                rating=r.rating,
                review_text=r.review_text,
                created_at=r.created_at,
                reviewer=ReviewerBrief.model_validate(r.reviewer) if r.reviewer else None,
                book_title=r.book.title if r.book else None,
                book_id=r.book_id,
            )
            for r in reviews
        ]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return ReviewPaginatedResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def get_user_reviews(self, user_id: int, pagination: PaginationParams) -> ReviewPaginatedResponse:
        """Community Ratings tab on user profile."""
        reviews, total = self.repo.get_reviews_for_user(user_id, pagination.offset, pagination.per_page)
        items = [
            ReviewResponse(
                id=r.id,
                rating=r.rating,
                review_text=r.review_text,
                created_at=r.created_at,
                reviewer=ReviewerBrief.model_validate(r.reviewer) if r.reviewer else None,
                book_title=r.book.title if r.book else None,
                book_id=r.book_id,
            )
            for r in reviews
        ]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return ReviewPaginatedResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )
