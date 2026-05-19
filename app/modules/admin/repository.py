"""
Admin module repository — covers:
- AppConfig key/value CRUD (existing)
- AdminManagementRepository: users, books, reviews, stats
"""
import math
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.modules.admin.model import AppConfig, ContactMessage
from app.modules.users.model import User
from app.modules.books.model import Book, Review
from app.modules.borrowing.model import BorrowRequest
from app.modules.admin.model import ContactMessage


# ─── Existing AppConfig Repository ───────────────────────

class AdminConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[AppConfig]:
        return self.db.query(AppConfig).order_by(AppConfig.key).all()

    def get_by_key(self, key: str) -> AppConfig | None:
        return self.db.query(AppConfig).filter(AppConfig.key == key).first()

    def set_value(self, key: str, value: str) -> AppConfig:
        config = self.get_by_key(key)
        if config:
            config.value = value
        else:
            config = AppConfig(key=key, value=value)
            self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def seed_defaults(self, defaults: dict[str, tuple[str, str]]) -> None:
        """Seed default configs if they don't exist. defaults = {key: (value, description)}"""
        for key, (value, description) in defaults.items():
            existing = self.get_by_key(key)
            if not existing:
                config = AppConfig(key=key, value=value, description=description)
                self.db.add(config)
        self.db.commit()


# ─── Admin Management Repository ─────────────────────────

class AdminManagementRepository:
    """Repository for admin user/book/review management operations."""

    def __init__(self, db: Session):
        self.db = db

    # ── Platform Stats ────────────────────────────────────

    def get_platform_stats(self) -> dict:
        """Aggregate platform-wide stats for the admin dashboard."""
        now = datetime.now(timezone.utc)

        total_users = self.db.query(func.count(User.id)).scalar() or 0
        active_users = self.db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
        suspended_users = self.db.query(func.count(User.id)).filter(User.is_active == False).scalar() or 0

        total_books = self.db.query(func.count(Book.id)).scalar() or 0
        available_books = self.db.query(func.count(Book.id)).filter(Book.availability == "available").scalar() or 0
        borrowed_books = self.db.query(func.count(Book.id)).filter(Book.availability == "borrowed").scalar() or 0

        total_borrows = self.db.query(func.count(BorrowRequest.id)).scalar() or 0
        pending_borrows = self.db.query(func.count(BorrowRequest.id)).filter(BorrowRequest.status == "pending").scalar() or 0
        active_borrows = self.db.query(func.count(BorrowRequest.id)).filter(BorrowRequest.status == "active").scalar() or 0

        # Overdue = active borrows past their due_date
        overdue_borrows = self.db.query(func.count(BorrowRequest.id)).filter(
            and_(BorrowRequest.status == "active", BorrowRequest.due_date < now)
        ).scalar() or 0

        total_reviews = self.db.query(func.count(Review.id)).scalar() or 0
        avg_rating_result = self.db.query(func.avg(Review.rating)).scalar()
        avg_platform_rating = round(float(avg_rating_result), 2) if avg_rating_result else 0.0

        return {
            "total_users": total_users,
            "active_users": active_users,
            "suspended_users": suspended_users,
            "total_books": total_books,
            "available_books": available_books,
            "borrowed_books": borrowed_books,
            "total_borrow_requests": total_borrows,
            "pending_borrow_requests": pending_borrows,
            "active_borrow_requests": active_borrows,
            "overdue_borrow_requests": overdue_borrows,
            "total_reviews": total_reviews,
            "avg_platform_rating": avg_platform_rating,
        }

    # ── User Management ───────────────────────────────────

    def get_all_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[User], int]:
        """Return paginated user list with optional filters."""
        query = self.db.query(User)

        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(User.full_name.ilike(term), User.email.ilike(term))
            )
        if role:
            query = query.filter(User.role == role)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        total = query.count()
        items = query.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def suspend_user(self, user_id: int) -> Optional[User]:
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = False
            self.db.commit()
            self.db.refresh(user)
        return user

    def activate_user(self, user_id: int) -> Optional[User]:
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = True
            self.db.commit()
            self.db.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        self.db.delete(user)
        self.db.commit()
        return True

    def get_user_stats(self, user: User) -> dict:
        """Compute stats for a single user."""
        books_uploaded = self.db.query(func.count(Book.id)).filter(Book.owner_id == user.id).scalar() or 0
        books_available = self.db.query(func.count(Book.id)).filter(
            Book.owner_id == user.id, Book.availability == "available"
        ).scalar() or 0
        books_borrowed = self.db.query(func.count(BorrowRequest.id)).filter(
            BorrowRequest.borrower_id == user.id,
            BorrowRequest.status.in_(["active", "returned", "confirmed"]),
        ).scalar() or 0
        reviews_written = self.db.query(func.count(Review.id)).filter(Review.reviewer_id == user.id).scalar() or 0
        reviews_received = self.db.query(func.count(Review.id)).filter(Review.reviewee_id == user.id).scalar() or 0
        return {
            "books_uploaded": books_uploaded,
            "books_available": books_available,
            "books_borrowed": books_borrowed,
            "reviews_written": reviews_written,
            "reviews_received": reviews_received,
        }

    # ── Book Management ───────────────────────────────────

    def get_all_books(
        self,
        search: Optional[str] = None,
        availability: Optional[str] = None,
        genre_id: Optional[int] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Book], int]:
        """Return paginated book list with optional filters."""
        query = self.db.query(Book)

        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(Book.title.ilike(term), Book.author_name.ilike(term))
            )
        if availability:
            query = query.filter(Book.availability == availability)
        if genre_id:
            query = query.filter(Book.genre_id == genre_id)

        total = query.count()
        items = query.order_by(Book.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        return self.db.query(Book).filter(Book.id == book_id).first()

    def update_book(self, book_id: int, availability: Optional[str], description: Optional[str]) -> Optional[Book]:
        book = self.get_book_by_id(book_id)
        if not book:
            return None
        if availability is not None:
            book.availability = availability
        if description is not None:
            book.description = description
        self.db.commit()
        self.db.refresh(book)
        return book

    def delete_book(self, book_id: int) -> tuple[bool, Optional[int]]:
        """Delete book, return (success, owner_id)."""
        book = self.get_book_by_id(book_id)
        if not book:
            return False, None
        owner_id = book.owner_id
        self.db.delete(book)
        self.db.commit()
        return True, owner_id

    # ── Reviews Management ────────────────────────────────

    def get_all_reviews(
        self,
        book_id: Optional[int] = None,
        min_rating: Optional[float] = None,
        max_rating: Optional[float] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Review], int]:
        """Return paginated review list with optional filters."""
        query = self.db.query(Review)

        if book_id:
            query = query.filter(Review.book_id == book_id)
        if min_rating is not None:
            query = query.filter(Review.rating >= min_rating)
        if max_rating is not None:
            query = query.filter(Review.rating <= max_rating)

        total = query.count()
        items = query.order_by(Review.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total

    def get_review_by_id(self, review_id: int) -> Optional[Review]:
        return self.db.query(Review).filter(Review.id == review_id).first()

    def delete_review_and_recalculate(self, review_id: int) -> tuple[bool, Optional[int], Optional[int]]:
        """
        Delete a review and recalculate avg_rating for the affected book and reviewee.
        Returns (success, book_id, reviewee_id).
        """
        review = self.get_review_by_id(review_id)
        if not review:
            return False, None, None

        book_id = review.book_id
        reviewee_id = review.reviewee_id

        self.db.delete(review)
        self.db.flush()

        # Recalculate book avg_rating
        book = self.db.query(Book).filter(Book.id == book_id).first()
        if book:
            new_book_avg = self.db.query(func.avg(Review.rating)).filter(Review.book_id == book_id).scalar()
            book.avg_rating = round(float(new_book_avg), 2) if new_book_avg else 0.0

        # Recalculate reviewee avg_rating
        reviewee = self.db.query(User).filter(User.id == reviewee_id).first()
        if reviewee:
            new_user_avg = self.db.query(func.avg(Review.rating)).filter(Review.reviewee_id == reviewee_id).scalar()
            reviewee.avg_rating = round(float(new_user_avg), 2) if new_user_avg else 0.0

        self.db.commit()
        return True, book_id, reviewee_id

    # ── Notification Helpers ──────────────────────────────

    def get_all_active_users(self) -> list[User]:
        """Get all active users for broadcast notifications."""
        return self.db.query(User).filter(User.is_active == True).all()

    # ── Contact Messages ──────────────────────────────────

    def get_contact_messages(self, page: int = 1, size: int = 20) -> tuple[list[ContactMessage], int]:
        query = self.db.query(ContactMessage)
        total = query.count()
        items = query.order_by(ContactMessage.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total

    def get_contact_message_by_id(self, message_id: int) -> Optional[ContactMessage]:
        return self.db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
