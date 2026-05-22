"""
Contact module repository — database operations for contact submissions.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.modules.contact.model import Contact


class ContactRepository:
    def __init__(self, db: Session):
        self.db = db

    def _base_query(self):
        return (
            self.db.query(Contact)
            .options(joinedload(Contact.user))
        )

    def get_all(self, offset: int = 0, limit: int = 20) -> tuple[list[Contact], int]:
        """Get all contact submissions, newest first."""
        query = self._base_query()
        total = query.count()
        items = query.order_by(desc(Contact.created_at)).offset(offset).limit(limit).all()
        return items, total

    def get_by_id(self, contact_id: int) -> Contact | None:
        """Get a single contact submission by ID."""
        return self._base_query().filter(Contact.id == contact_id).first()

    def create(self, data: dict) -> Contact:
        """Create a new contact submission."""
        contact = Contact(**data)
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return self.get_by_id(contact.id)
