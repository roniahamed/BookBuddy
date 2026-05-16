"""
Users module repository — optimized database operations.
No soft-delete: hard delete with CASCADE.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case
from app.modules.users.model import User, UserSettings


class UserRepository:
    """Handles all user-related database queries with optimization."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_with_settings(self, user_id: int) -> User | None:
        """Get user with settings eager-loaded (single query)."""
        return (
            self.db.query(User)
            .options(joinedload(User.settings))
            .filter(User.id == user_id)
            .first()
        )

    def get_user_profile_stats(self, user_id: int) -> dict:
        """
        Get profile stats in a SINGLE aggregation query.
        Returns: books_uploaded, books_available, books_borrowed
        """
        from app.modules.books.model import Book
        from app.modules.borrowing.model import BorrowRequest

        # Single query with conditional aggregation
        stats = self.db.query(
            func.count(Book.id).label("books_uploaded"),
            func.count(case((Book.availability == "available", 1))).label("books_available"),
        ).filter(
            Book.owner_id == user_id,
        ).first()

        # Count books the user has borrowed (active or returned)
        borrowed_count = self.db.query(func.count(BorrowRequest.id)).filter(
            BorrowRequest.borrower_id == user_id,
            BorrowRequest.status.in_(["active", "returned", "confirmed"]),
        ).scalar() or 0

        return {
            "books_uploaded": stats.books_uploaded if stats else 0,
            "books_available": stats.books_available if stats else 0,
            "books_borrowed": borrowed_count,
        }

    def update_user(self, user_id: int, update_data: dict) -> User:
        """Update user fields (only non-None values)."""
        update_data = {k: v for k, v in update_data.items() if v is not None}
        if update_data:
            self.db.query(User).filter(User.id == user_id).update(update_data)
            self.db.commit()
        return self.get_user_with_settings(user_id)

    def get_settings(self, user_id: int) -> UserSettings | None:
        """Get user settings."""
        return self.db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

    def update_settings(self, user_id: int, update_data: dict) -> UserSettings:
        """Update user settings (only non-None values)."""
        update_data = {k: v for k, v in update_data.items() if v is not None}
        if update_data:
            self.db.query(UserSettings).filter(UserSettings.user_id == user_id).update(update_data)
            self.db.commit()
        return self.get_settings(user_id)

    def hard_delete_user(self, user_id: int) -> None:
        """
        HARD DELETE: permanently remove user and all related data.
        CASCADE on foreign keys handles books, borrow_requests, reviews, wishlist, conversations.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            self.db.delete(user)
            self.db.commit()

    def update_password(self, user_id: int, password_hash: str) -> None:
        """Update user password hash."""
        self.db.query(User).filter(User.id == user_id).update(
            {"password_hash": password_hash}
        )
        self.db.commit()

    def get_public_profile(self, user_id: int) -> User | None:
        """Get public profile (without settings)."""
        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .first()
        )
