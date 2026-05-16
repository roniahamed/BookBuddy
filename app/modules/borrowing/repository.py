"""
Borrowing module repository — optimized database operations for borrow requests.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from app.modules.borrowing.model import BorrowRequest
from app.modules.books.model import Book


class BorrowRepository:
    """Handles all borrowing-related database queries."""

    def __init__(self, db: Session):
        self.db = db

    def _base_query(self):
        """Base query with eager loading for book and borrower."""
        return (
            self.db.query(BorrowRequest)
            .options(
                joinedload(BorrowRequest.book),
                joinedload(BorrowRequest.borrower),
            )
        )

    def get_by_id(self, request_id: int) -> BorrowRequest | None:
        """Get single borrow request with relationships."""
        return self._base_query().filter(BorrowRequest.id == request_id).first()

    def get_borrowed_by_user(
        self, user_id: int, offset: int = 0, limit: int = 20
    ) -> tuple[list[BorrowRequest], int]:
        """
        Get books borrowed by a user (Borrowed tab).
        Shows active and returned requests.
        """
        query = (
            self._base_query()
            .filter(
                BorrowRequest.borrower_id == user_id,
                BorrowRequest.status.in_(["pending", "approved", "active", "returned"]),
            )
        )
        total = query.count()
        items = query.order_by(desc(BorrowRequest.requested_at)).offset(offset).limit(limit).all()
        return items, total

    def get_lent_out_by_user(
        self, user_id: int, offset: int = 0, limit: int = 20
    ) -> tuple[list[BorrowRequest], int]:
        """
        Get books lent out by a user (Lent Out tab).
        Joins on book.owner_id to find books owned by user that are borrowed.
        """
        query = (
            self._base_query()
            .join(Book, BorrowRequest.book_id == Book.id)
            .filter(
                Book.owner_id == user_id,
                BorrowRequest.status.in_(["pending", "approved", "active", "returned"]),
            )
        )
        total = query.count()
        items = query.order_by(desc(BorrowRequest.requested_at)).offset(offset).limit(limit).all()
        return items, total

    def has_active_borrow(self, book_id: int) -> bool:
        """Check if a book already has an active borrow (prevents double-borrow)."""
        return self.db.query(
            self.db.query(BorrowRequest).filter(
                BorrowRequest.book_id == book_id,
                BorrowRequest.status.in_(["pending", "approved", "active"]),
            ).exists()
        ).scalar()

    def has_pending_request(self, borrower_id: int, book_id: int) -> bool:
        """Check if user already has a pending request for this book."""
        return self.db.query(
            self.db.query(BorrowRequest).filter(
                BorrowRequest.borrower_id == borrower_id,
                BorrowRequest.book_id == book_id,
                BorrowRequest.status.in_(["pending", "approved"]),
            ).exists()
        ).scalar()

    def create_borrow_request(self, borrower_id: int, book_id: int) -> BorrowRequest:
        """Create a new borrow request."""
        borrow = BorrowRequest(
            book_id=book_id,
            borrower_id=borrower_id,
            status="pending",
        )
        self.db.add(borrow)
        self.db.commit()
        self.db.refresh(borrow)
        return borrow

    def update_status(self, request_id: int, status: str, **kwargs) -> BorrowRequest:
        """Update borrow request status with timestamp fields."""
        update_data = {"status": status, **kwargs}
        self.db.query(BorrowRequest).filter(BorrowRequest.id == request_id).update(update_data)
        self.db.commit()
        return self.get_by_id(request_id)

    def update_book_availability(self, book_id: int, availability: str) -> None:
        """Update book's availability status."""
        self.db.query(Book).filter(Book.id == book_id).update({"availability": availability})
        self.db.commit()
