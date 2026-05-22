"""
Contact module API endpoints.

Covers:
- GET    /contact        — List all submissions (admin; requires auth)
- GET    /contact/{id}   — Get single submission (admin; requires auth)
- POST   /contact        — Submit a new contact message (public or authenticated)
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional
from app.core.dependencies import get_db
from app.modules.auth.dependencies import get_current_user, get_current_user_optional
from app.modules.users.model import User
from app.modules.contact.service import ContactService
from app.modules.contact.schema import (
    ContactResponse, ContactPaginatedResponse, ContactCreateRequest,
)
from app.shared.pagination import PaginationParams

router = APIRouter()


@router.get(
    "",
    response_model=ContactPaginatedResponse,
    summary="List all contact submissions",
    description=(
        "Get all contact form submissions, newest first, paginated. "
        "Intended for admin / support use. Requires authentication."
    ),
)
async def list_contacts(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ContactService(db)
    return service.list_contacts(pagination)


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Get a single contact submission",
    description="Get full details of a specific contact form submission by its ID. Requires authentication.",
    responses={404: {"description": "Contact submission not found"}},
)
async def get_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ContactService(db)
    return service.get_contact(contact_id)


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a contact message",
    description=(
        "Submit a contact form message (Contact Us page). "
        "Authentication is optional — if authenticated, the submission is linked to the user's account. "
        "Returns the created submission with its assigned ID and status."
    ),
)
async def create_contact(
    data: ContactCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    service = ContactService(db)
    return service.create_contact(data, current_user)
