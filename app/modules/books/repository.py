"""
Books module repository — optimized database operations.
Handles search, filtering, nearby calculation, and eager loading.
No soft-delete: hard delete for books.
"""
import math
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload, Query
from sqlalchemy import func, case, or_, and_, desc, asc
from app.modules.books.model import Book, Genre, Wishlist, Review, Author
from app.modules.users.model import User
from app.modules.books.filters import BookFilters


def _haversine_distance(lat1: float, lon1: float, lat2_col, lon2_col):
    """
    SQL expression for Haversine distance in km.
    For PostgreSQL — uses SQL math functions.
    """
    R = 6371
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)

    lat2_rad = func.radians(lat2_col)
    lon2_rad = func.radians(lon2_col)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        func.power(func.sin(dlat / 2), 2)
        + func.cos(lat1_rad) * func.cos(lat2_rad) * func.power(func.sin(dlon / 2), 2)
    )
    c = 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))
    return R * c


class BookRepository:
    """Handles all book-related database queries with query optimization."""

    def __init__(self, db: Session):
        self.db = db

    def _base_book_query(self) -> Query:
        """Base query with eager loading for owner and genre (avoids N+1)."""
        return (
            self.db.query(Book)
            .options(
                joinedload(Book.owner),
                joinedload(Book.genre),
                joinedload(Book.author),
            )
        )

    def get_books_filtered(
        self,
        filters: BookFilters,
        offset: int = 0,
        limit: int = 20,
        user_id: Optional[int] = None,
    ) -> tuple[list[Book], int]:
        """Browse Books with search, filter, sort, and pagination."""
        query = self._base_book_query()

        # Search (title, author, genre name)
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.outerjoin(Genre, Book.genre_id == Genre.id).outerjoin(Author, Book.author_id == Author.id).filter(
                or_(
                    Book.title.ilike(search_term),
                    Author.name.ilike(search_term),
                    Genre.name.ilike(search_term),
                )
            )

        if filters.genre_id:
            query = query.filter(Book.genre_id == filters.genre_id)

        if filters.condition:
            query = query.filter(Book.condition == filters.condition)

        if filters.availability:
            query = query.filter(Book.availability == filters.availability)

        if filters.user_lat and filters.user_lon and filters.radius_km:
            lat_delta = filters.radius_km / 111.0
            lon_delta = filters.radius_km / (111.0 * math.cos(math.radians(filters.user_lat)))
            query = query.filter(
                Book.latitude.isnot(None),
                Book.longitude.isnot(None),
                Book.latitude.between(filters.user_lat - lat_delta, filters.user_lat + lat_delta),
                Book.longitude.between(filters.user_lon - lon_delta, filters.user_lon + lon_delta),
            )

        total = query.count()

        # Sorting
        if filters.sort_by == "top_rated":
            query = query.order_by(desc(Book.avg_rating))
        elif filters.sort_by == "title_asc":
            query = query.order_by(asc(Book.title))
        elif filters.sort_by == "title_desc":
            query = query.order_by(desc(Book.title))
        elif filters.sort_by == "nearby" and filters.user_lat and filters.user_lon:
            distance = _haversine_distance(
                filters.user_lat, filters.user_lon, Book.latitude, Book.longitude
            )
            query = query.filter(Book.latitude.isnot(None)).order_by(distance)
        else:
            query = query.order_by(desc(Book.created_at))

        books = query.offset(offset).limit(limit).all()
        return books, total

    def get_book_by_id(self, book_id: int) -> Book | None:
        """Get single book with all relationships eager-loaded."""
        return self._base_book_query().filter(Book.id == book_id).first()

    def get_books_by_owner(self, owner_id: int, offset: int = 0, limit: int = 20) -> tuple[list[Book], int]:
        """Get books uploaded by a specific user."""
        query = self._base_book_query().filter(Book.owner_id == owner_id)
        total = query.count()
        books = query.order_by(desc(Book.created_at)).offset(offset).limit(limit).all()
        return books, total

    def get_nearby_books(
        self, lat: float, lon: float, radius_km: float = 50, offset: int = 0, limit: int = 20
    ) -> tuple[list[Book], int]:
        """Get books near a location, sorted by distance."""
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.001))

        query = (
            self._base_book_query()
            .filter(
                Book.latitude.isnot(None),
                Book.longitude.isnot(None),
                Book.latitude.between(lat - lat_delta, lat + lat_delta),
                Book.longitude.between(lon - lon_delta, lon + lon_delta),
                Book.availability == "available",
            )
        )
        total = query.count()

        distance = _haversine_distance(lat, lon, Book.latitude, Book.longitude)
        books = query.order_by(distance).offset(offset).limit(limit).all()
        return books, total

    def get_recommended_books(self, user_id: int, offset: int = 0, limit: int = 20) -> tuple[list[Book], int]:
        """Recommended books based on user's borrowing history genres."""
        from app.modules.borrowing.model import BorrowRequest

        borrowed_genre_ids = (
            self.db.query(Book.genre_id)
            .join(BorrowRequest, BorrowRequest.book_id == Book.id)
            .filter(
                BorrowRequest.borrower_id == user_id,
                Book.genre_id.isnot(None),
            )
            .distinct()
            .all()
        )
        genre_ids = [g[0] for g in borrowed_genre_ids]

        if genre_ids:
            query = (
                self._base_book_query()
                .filter(
                    Book.genre_id.in_(genre_ids),
                    Book.owner_id != user_id,
                    Book.availability == "available",
                )
            )
            total = query.count()
            if total > 0:
                books = query.order_by(desc(Book.avg_rating)).offset(offset).limit(limit).all()
                return books, total

        query = (
            self._base_book_query()
            .filter(Book.availability == "available", Book.owner_id != user_id)
        )
        total = query.count()
        books = query.order_by(desc(Book.avg_rating), desc(Book.created_at)).offset(offset).limit(limit).all()
        return books, total

    def get_new_arrivals(self, limit: int = 20, offset: int = 0) -> tuple[list[Book], int]:
        query = self._base_book_query().filter(Book.availability == "available")
        total = query.count()
        books = query.order_by(desc(Book.created_at)).offset(offset).limit(limit).all()
        return books, total

    def get_top_rated(self, limit: int = 20, offset: int = 0) -> tuple[list[Book], int]:
        query = self._base_book_query().filter(Book.availability == "available")
        total = query.count()
        books = query.order_by(desc(Book.avg_rating), desc(Book.created_at)).offset(offset).limit(limit).all()
        return books, total

    def create_book(self, owner_id: int, data: dict) -> Book:
        book = Book(owner_id=owner_id, **data)
        self.db.add(book)
        self.db.commit()
        self.db.refresh(book)
        return self.get_book_by_id(book.id)

    def update_book(self, book_id: int, data: dict) -> Book:
        data = {k: v for k, v in data.items() if v is not None}
        if data:
            self.db.query(Book).filter(Book.id == book_id).update(data)
            self.db.commit()
        return self.get_book_by_id(book_id)

    def hard_delete_book(self, book_id: int) -> None:
        """HARD DELETE a book — permanently removes it and all related data."""
        book = self.db.query(Book).filter(Book.id == book_id).first()
        if book:
            self.db.delete(book)
            self.db.commit()

    # ─── Genres ──────────────────────────────────────────
    def get_all_genres(self) -> list[Genre]:
        return self.db.query(Genre).order_by(Genre.name).all()

    def get_or_create_genre(self, name: str) -> Genre:
        genre = self.db.query(Genre).filter(Genre.name == name).first()
        if not genre:
            genre = Genre(name=name)
            self.db.add(genre)
            self.db.commit()
            self.db.refresh(genre)
        return genre

    # ─── Authors ─────────────────────────────────────────
    def get_all_authors(self) -> list[Author]:
        return self.db.query(Author).order_by(Author.name).all()

    def get_or_create_author(self, name: str) -> Author:
        author = self.db.query(Author).filter(Author.name == name).first()
        if not author:
            author = Author(name=name)
            self.db.add(author)
            self.db.commit()
            self.db.refresh(author)
        return author

    # ─── Wishlist ────────────────────────────────────────
    def get_wishlist(self, user_id: int, offset: int = 0, limit: int = 20) -> tuple[list[Wishlist], int]:
        query = (
            self.db.query(Wishlist)
            .options(
                joinedload(Wishlist.book).joinedload(Book.owner),
                joinedload(Wishlist.book).joinedload(Book.genre),
            )
            .filter(Wishlist.user_id == user_id)
            .join(Book, Wishlist.book_id == Book.id)
        )
        total = query.count()
        items = query.order_by(desc(Wishlist.created_at)).offset(offset).limit(limit).all()
        return items, total

    def is_wishlisted(self, user_id: int, book_id: int) -> bool:
        return self.db.query(
            self.db.query(Wishlist).filter(
                Wishlist.user_id == user_id, Wishlist.book_id == book_id
            ).exists()
        ).scalar()

    def add_to_wishlist(self, user_id: int, book_id: int) -> Wishlist:
        item = Wishlist(user_id=user_id, book_id=book_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_from_wishlist(self, user_id: int, book_id: int) -> None:
        self.db.query(Wishlist).filter(
            Wishlist.user_id == user_id, Wishlist.book_id == book_id
        ).delete()
        self.db.commit()

    # ─── Reviews ─────────────────────────────────────────
    def get_reviews_for_book(self, book_id: int, offset: int = 0, limit: int = 20) -> tuple[list[Review], int]:
        query = (
            self.db.query(Review)
            .options(joinedload(Review.reviewer))
            .filter(Review.book_id == book_id)
        )
        total = query.count()
        items = query.order_by(desc(Review.created_at)).offset(offset).limit(limit).all()
        return items, total

    def get_reviews_for_user(self, user_id: int, offset: int = 0, limit: int = 20) -> tuple[list[Review], int]:
        query = (
            self.db.query(Review)
            .options(joinedload(Review.reviewer), joinedload(Review.book))
            .filter(Review.reviewee_id == user_id)
        )
        total = query.count()
        items = query.order_by(desc(Review.created_at)).offset(offset).limit(limit).all()
        return items, total

    def create_review(self, data: dict) -> Review:
        review = Review(**data)
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def review_exists(self, borrow_request_id: int, reviewer_id: int) -> bool:
        return self.db.query(
            self.db.query(Review).filter(
                Review.borrow_request_id == borrow_request_id,
                Review.reviewer_id == reviewer_id,
            ).exists()
        ).scalar()

    def update_book_avg_rating(self, book_id: int) -> None:
        avg = self.db.query(func.avg(Review.rating)).filter(Review.book_id == book_id).scalar()
        self.db.query(Book).filter(Book.id == book_id).update(
            {"avg_rating": round(avg, 2) if avg else 0.0}
        )
        self.db.commit()

    def update_user_avg_rating(self, user_id: int) -> None:
        avg = self.db.query(func.avg(Review.rating)).filter(Review.reviewee_id == user_id).scalar()
        self.db.query(User).filter(User.id == user_id).update(
            {"avg_rating": round(avg, 2) if avg else 0.0}
        )
        self.db.commit()

    def get_reviews_count_for_book(self, book_id: int) -> int:
        return self.db.query(func.count(Review.id)).filter(Review.book_id == book_id).scalar() or 0

    def get_user_wishlisted_book_ids(self, user_id: int) -> set[int]:
        results = self.db.query(Wishlist.book_id).filter(Wishlist.user_id == user_id).all()
        return {r[0] for r in results}
