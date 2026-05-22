"""
Contact module service — business logic for contact form submissions.
"""
import math
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.modules.contact.repository import ContactRepository
from app.modules.contact.schema import (
    ContactResponse, ContactPaginatedResponse, ContactCreateRequest, ContactUserBrief,
)
from app.modules.users.model import User
from app.shared.pagination import PaginationParams


def _contact_to_response(c) -> ContactResponse:
    user_brief = None
    if c.user:
        user_brief = ContactUserBrief(
            id=c.user.id,
            full_name=c.user.full_name,
            email=c.user.email,
        )
    return ContactResponse(
        id=c.id,
        name=c.name,
        email=c.email,
        subject=c.subject,
        message=c.message,
        status=c.status,
        user=user_brief,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


class ContactService:
    def __init__(self, db: Session):
        self.repo = ContactRepository(db)

    def list_contacts(self, pagination: PaginationParams) -> ContactPaginatedResponse:
        """List all contact submissions (admin use)."""
        items, total = self.repo.get_all(pagination.offset, pagination.per_page)
        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return ContactPaginatedResponse(
            items=[_contact_to_response(c) for c in items],
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            pages=pages,
            has_next=pagination.page < pages,
            has_prev=pagination.page > 1,
        )

    def get_contact(self, contact_id: int) -> ContactResponse:
        """Get a single contact submission by ID."""
        c = self.repo.get_by_id(contact_id)
        if not c:
            raise HTTPException(status_code=404, detail=f"Contact submission id={contact_id} not found")
        return _contact_to_response(c)

    def create_contact(
        self, data: ContactCreateRequest, current_user: User = None
    ) -> ContactResponse:
        """Submit a new contact form message."""
        payload = {
            "name": data.name,
            "email": data.email,
            "subject": data.subject,
            "message": data.message,
            "status": "open",
            "user_id": current_user.id if current_user else None,
        }
        c = self.repo.create(payload)
        return _contact_to_response(c)
