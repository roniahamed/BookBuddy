"""
Borrowing module API endpoints.

Covers the full borrow lifecycle:
- POST   /borrow-requests              — Request to borrow a book
- GET    /borrow-requests/borrowed      — My borrowed books (Borrowed tab)
- GET    /borrow-requests/lent-out      — My lent out books (Lent Out tab)
- GET    /borrow-requests/{id}          — Single borrow request detail
- PATCH  /borrow-requests/{id}/approve  — Owner approves request
- PATCH  /borrow-requests/{id}/reject   — Owner rejects request
- PATCH  /borrow-requests/{id}/return   — Borrower marks as returned
- PATCH  /borrow-requests/{id}/confirm  — Owner confirms book received
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.borrowing.service import BorrowService
from app.modules.borrowing.schema import (
    BorrowRequestResponse, BorrowRequestCreateRequest, BorrowRequestCreateResponse,
    BorrowRequestPaginatedResponse, BorrowStatusUpdateResponse,
)
from app.shared.pagination import PaginationParams

router = APIRouter()


@router.post(
    "",
    response_model=BorrowRequestCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request to borrow a book",
    description=(
        "Submit a request to borrow a book (REQUEST BOOK button). "
        "The book must be available and you cannot borrow your own books. "
        "Duplicate pending requests are not allowed."
    ),
    responses={
        400: {"description": "Book not available or trying to borrow own book"},
        404: {"description": "Book not found"},
        409: {"description": "Already have a pending request"},
    },
)
async def create_borrow_request(
    data: BorrowRequestCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BorrowService(db)
    return service.create_borrow_request(current_user, data)


@router.get(
    "/borrowed",
    response_model=BorrowRequestPaginatedResponse,
    summary="My borrowed books",
    description=(
        "Get all books you have borrowed (Borrowed tab on Profile screen). "
        "Shows countdown timer 'Return in X days Y Hours' for active borrows. "
        "Includes 'Mark as Returned' action for active loans."
    ),
)
async def get_borrowed_books(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BorrowService(db)
    return service.get_borrowed_books(current_user, pagination)


@router.get(
    "/lent-out",
    response_model=BorrowRequestPaginatedResponse,
    summary="My lent out books",
    description=(
        "Get all books you have lent out to others (Lent Out tab on Profile screen). "
        "Shows 'Expected back in X days Y Hours' countdown for active loans. "
        "Includes 'Confirm Received' action for returned books."
    ),
)
async def get_lent_out_books(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BorrowService(db)
    return service.get_lent_out_books(current_user, pagination)


@router.get(
    "/{request_id}",
    response_model=BorrowRequestResponse,
    summary="Borrow request details",
    description="Get details of a specific borrow request. Only accessible by the borrower or book owner.",
    responses={
        403: {"description": "Access denied"},
        404: {"description": "Borrow request not found"},
    },
)
async def get_borrow_detail(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BorrowService(db)
    return service.get_borrow_detail(request_id, current_user)


@router.patch(
    "/{request_id}/approve",
    response_model=BorrowStatusUpdateResponse,
    summary="Approve borrow request",
    description=(
        "Book owner approves a pending borrow request. "
        "Automatically starts the loan: sets status to 'active', "
        "records borrowed_at timestamp, and calculates due_date "
        "(borrowed_at + borrow_duration_days). "
        "The book's availability changes to 'borrowed'."
    ),
    responses={
        400: {"description": "Invalid status transition"},
        403: {"description": "Not the book owner"},
        404: {"description": "Request not found"},
    },
)
async def approve_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BorrowService(db)
    return service.approve_request(request_id, current_user)


@router.patch(
    "/{request_id}/reject",
    response_model=BorrowStatusUpdateResponse,
    summary="Reject borrow request",
    description="Book owner rejects a pending borrow request. Status changes to 'cancelled'.",
    responses={
        400: {"description": "Invalid status transition"},
        403: {"description": "Not the book owner"},
        404: {"description": "Request not found"},
    },
)
async def reject_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BorrowService(db)
    return service.reject_request(request_id, current_user)


@router.patch(
    "/{request_id}/return",
    response_model=BorrowStatusUpdateResponse,
    summary="Mark book as returned",
    description=(
        "Borrower marks a book as returned (Mark as Returned button on Borrowed tab). "
        "Status changes from 'active' to 'returned'. "
        "Owner still needs to confirm receipt."
    ),
    responses={
        400: {"description": "Invalid status transition"},
        403: {"description": "Not the borrower"},
        404: {"description": "Request not found"},
    },
)
async def mark_returned(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BorrowService(db)
    return service.mark_returned(request_id, current_user)


@router.patch(
    "/{request_id}/confirm",
    response_model=BorrowStatusUpdateResponse,
    summary="Confirm book received back",
    description=(
        "Book owner confirms the returned book has been received "
        "(Confirm Received button on Lent Out tab). "
        "Status changes to 'confirmed'. Book becomes 'available' again. "
        "Credits are awarded: +5 to borrower, +10 to lender."
    ),
    responses={
        400: {"description": "Invalid status transition"},
        403: {"description": "Not the book owner"},
        404: {"description": "Request not found"},
    },
)
async def confirm_received(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BorrowService(db)
    return service.confirm_received(request_id, current_user)


@router.post(
    "/{request_id}/cancel",
    response_model=BorrowStatusUpdateResponse,
    summary="Cancel borrow request",
    description=(
        "Borrower cancels a pending borrow request. "
        "Status changes to 'cancelled'."
    ),
    responses={
        400: {"description": "Invalid status transition"},
        403: {"description": "Not the borrower"},
        404: {"description": "Request not found"},
    },
)
async def cancel_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BorrowService(db)
    return service.cancel_request(request_id, current_user)
