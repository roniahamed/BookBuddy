"""
Borrowing module service — business logic for the borrow lifecycle.

State machine: pending → approved → active → returned → confirmed
                 ↘ cancelled
"""
import math
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.modules.borrowing.repository import BorrowRepository
from app.modules.borrowing.model import BorrowRequest
from app.modules.borrowing.schema import (
    BorrowRequestResponse, BorrowRequestCreateRequest, BorrowRequestCreateResponse,
    BorrowRequestPaginatedResponse, BorrowStatusUpdateResponse,
    BorrowBookBrief, BorrowUserBrief,
)
from app.modules.books.model import Book
from app.modules.users.model import User
from app.shared.pagination import PaginationParams


def _compute_time_remaining(due_date: datetime) -> str | None:
    """
    Compute 'Return in X days Y Hours' string from due_date.
    Returns 'Overdue' if past due date.
    """
    if not due_date:
        return None

    now = datetime.now(timezone.utc)
    # Make due_date timezone-aware if it's not
    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=timezone.utc)
    
    delta = due_date - now

    if delta.total_seconds() <= 0:
        return "Overdue"

    days = delta.days
    hours = delta.seconds // 3600

    if days > 0:
        return f"{days} days {hours} Hours"
    elif hours > 0:
        return f"{hours} Hours"
    else:
        minutes = delta.seconds // 60
        return f"{minutes} Minutes"


def _borrow_to_response(borrow: BorrowRequest) -> BorrowRequestResponse:
    """Convert BorrowRequest model to response with computed fields."""
    book_brief = None
    if borrow.book:
        book_brief = BorrowBookBrief(
            id=borrow.book.id,
            title=borrow.book.title,
            author_name=borrow.book.author_name,
            front_cover_url=borrow.book.front_cover_url,
            description=borrow.book.description,
            avg_rating=borrow.book.avg_rating or 0.0,
        )

    borrower_brief = None
    if borrow.borrower:
        borrower_brief = BorrowUserBrief(
            id=borrow.borrower.id,
            full_name=borrow.borrower.full_name,
            avatar_url=borrow.borrower.avatar_url,
        )

    time_remaining = None
    if borrow.status == "active" and borrow.due_date:
        time_remaining = _compute_time_remaining(borrow.due_date)

    return BorrowRequestResponse(
        id=borrow.id,
        status=borrow.status,
        requested_at=borrow.requested_at,
        approved_at=borrow.approved_at,
        borrowed_at=borrow.borrowed_at,
        due_date=borrow.due_date,
        returned_at=borrow.returned_at,
        confirmed_at=borrow.confirmed_at,
        time_remaining=time_remaining,
        book=book_brief,
        borrower=borrower_brief,
    )


class BorrowService:
    """Handles borrow lifecycle business logic."""

    def __init__(self, db: Session):
        self.repo = BorrowRepository(db)
        self.db = db

    def create_borrow_request(self, user: User, data: BorrowRequestCreateRequest) -> BorrowRequestCreateResponse:
        """
        Request to borrow a book (REQUEST BOOK button).
        Validates: book exists, is available, user isn't the owner, no duplicate request.
        """
        from app.modules.books.repository import BookRepository
        book_repo = BookRepository(self.db)
        book = book_repo.get_book_by_id(data.book_id)

        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if book.owner_id == user.id:
            raise HTTPException(status_code=400, detail="You cannot borrow your own book")

        if book.availability != "available":
            raise HTTPException(status_code=400, detail="This book is not available for borrowing")

        if self.repo.has_pending_request(user.id, data.book_id):
            raise HTTPException(status_code=409, detail="You already have a pending request for this book")

        borrow = self.repo.create_borrow_request(user.id, data.book_id)
        return BorrowRequestCreateResponse(id=borrow.id, status=borrow.status)

    def get_borrowed_books(self, user: User, pagination: PaginationParams) -> BorrowRequestPaginatedResponse:
        """My borrowed books (Borrowed tab on Profile screen)."""
        items, total = self.repo.get_borrowed_by_user(user.id, pagination.offset, pagination.per_page)
        responses = [_borrow_to_response(b) for b in items]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BorrowRequestPaginatedResponse(
            items=responses, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def get_lent_out_books(self, user: User, pagination: PaginationParams) -> BorrowRequestPaginatedResponse:
        """My lent out books (Lent Out tab on Profile screen)."""
        items, total = self.repo.get_lent_out_by_user(user.id, pagination.offset, pagination.per_page)
        responses = [_borrow_to_response(b) for b in items]
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return BorrowRequestPaginatedResponse(
            items=responses, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def get_borrow_detail(self, request_id: int, user: User) -> BorrowRequestResponse:
        """Get single borrow request details."""
        borrow = self.repo.get_by_id(request_id)
        if not borrow:
            raise HTTPException(status_code=404, detail="Borrow request not found")

        # Only borrower or book owner can view
        if borrow.borrower_id != user.id and borrow.book.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return _borrow_to_response(borrow)

    def approve_request(self, request_id: int, user: User) -> BorrowStatusUpdateResponse:
        """
        Owner approves borrow request.
        Transition: pending → approved → active (auto-start)
        Sets due_date = now + borrow_duration_days.
        """
        borrow = self.repo.get_by_id(request_id)
        if not borrow:
            raise HTTPException(status_code=404, detail="Borrow request not found")

        if borrow.book.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Only the book owner can approve requests")

        if borrow.status != "pending":
            raise HTTPException(status_code=400, detail=f"Cannot approve a {borrow.status} request")

        now = datetime.now(timezone.utc)
        due_date = now + timedelta(days=borrow.book.borrow_duration_days or 30)

        borrow = self.repo.update_status(
            request_id, "active",
            approved_at=now,
            borrowed_at=now,
            due_date=due_date,
        )

        # Update book availability
        self.repo.update_book_availability(borrow.book_id, "borrowed")

        return BorrowStatusUpdateResponse(
            id=borrow.id,
            status="active",
            message=f"Request approved. Book is now active. Due date: {due_date.strftime('%Y-%m-%d')}",
        )

    def reject_request(self, request_id: int, user: User) -> BorrowStatusUpdateResponse:
        """
        Owner rejects/cancels borrow request.
        Transition: pending → cancelled
        """
        borrow = self.repo.get_by_id(request_id)
        if not borrow:
            raise HTTPException(status_code=404, detail="Borrow request not found")

        if borrow.book.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Only the book owner can reject requests")

        if borrow.status != "pending":
            raise HTTPException(status_code=400, detail=f"Cannot reject a {borrow.status} request")

        borrow = self.repo.update_status(request_id, "cancelled")
        return BorrowStatusUpdateResponse(
            id=borrow.id, status="cancelled", message="Borrow request rejected"
        )

    def cancel_request(self, request_id: int, user: User) -> BorrowStatusUpdateResponse:
        """
        Borrower cancels borrow request.
        Transition: pending → cancelled
        """
        borrow = self.repo.get_by_id(request_id)
        if not borrow:
            raise HTTPException(status_code=404, detail="Borrow request not found")

        if borrow.borrower_id != user.id:
            raise HTTPException(status_code=403, detail="Only the borrower can cancel their requests")

        if borrow.status != "pending":
            raise HTTPException(status_code=400, detail=f"Cannot cancel a {borrow.status} request")

        borrow = self.repo.update_status(request_id, "cancelled")
        return BorrowStatusUpdateResponse(
            id=borrow.id, status="cancelled", message="Borrow request cancelled"
        )

    def mark_returned(self, request_id: int, user: User) -> BorrowStatusUpdateResponse:
        """
        Borrower marks book as returned (Mark as Returned button on Borrowed tab).
        Transition: active → returned
        """
        borrow = self.repo.get_by_id(request_id)
        if not borrow:
            raise HTTPException(status_code=404, detail="Borrow request not found")

        if borrow.borrower_id != user.id:
            raise HTTPException(status_code=403, detail="Only the borrower can mark as returned")

        if borrow.status != "active":
            raise HTTPException(status_code=400, detail=f"Cannot return a {borrow.status} request")

        borrow = self.repo.update_status(
            request_id, "returned",
            returned_at=datetime.now(timezone.utc),
        )
        return BorrowStatusUpdateResponse(
            id=borrow.id, status="returned", message="Book marked as returned. Waiting for owner confirmation."
        )

    def confirm_received(self, request_id: int, user: User) -> BorrowStatusUpdateResponse:
        """
        Owner confirms book received back (Confirm Received button on Lent Out tab).
        Transition: returned → confirmed
        Sets book back to 'available'.
        Awards credits to both users (configured by admin via AppConfig).
        """
        borrow = self.repo.get_by_id(request_id)
        if not borrow:
            raise HTTPException(status_code=404, detail="Borrow request not found")

        if borrow.book.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Only the book owner can confirm receipt")

        if borrow.status != "returned":
            raise HTTPException(status_code=400, detail=f"Cannot confirm a {borrow.status} request")

        borrow = self.repo.update_status(
            request_id, "confirmed",
            confirmed_at=datetime.now(timezone.utc),
        )

        # Set book back to available
        self.repo.update_book_availability(borrow.book_id, "available")

        # ─── Read credit values from admin config (NO hardcoding) ────
        from app.modules.admin.service import AdminConfigService
        config_service = AdminConfigService(self.db)
        borrower_points = config_service.get_int("borrow_reward_borrower_points", 5)
        lender_points = config_service.get_int("borrow_reward_lender_points", 10)

        # Award credits
        self.db.query(User).filter(User.id == borrow.borrower_id).update(
            {"credits": User.credits + borrower_points}
        )
        self.db.query(User).filter(User.id == user.id).update(
            {"credits": User.credits + lender_points}
        )
        self.db.commit()

        # Send push notifications via Celery
        try:
            from app.background.tasks import send_push_notification_task
            borrower = self.db.query(User).filter(User.id == borrow.borrower_id).first()
            if borrower:
                send_push_notification_task.delay(
                    borrower.id,
                    "Book Return Confirmed! 🎉",
                    f"Your return has been confirmed. You earned {borrower_points} credits!",
                )
        except Exception:
            pass

        return BorrowStatusUpdateResponse(
            id=borrow.id, status="confirmed",
            message=f"Book return confirmed. Borrower earned {borrower_points} credits, you earned {lender_points} credits!",
        )
