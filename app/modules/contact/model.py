"""
Contact module SQLAlchemy model.
Stores contact form submissions from users or anonymous visitors.
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Contact(Base):
    """Contact form submission sent via the Contact Us page."""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="If submitted by a logged-in user; NULL for anonymous"
    )
    name = Column(String(150), nullable=False, comment="Submitter's name")
    email = Column(String(255), nullable=False, index=True, comment="Reply-to email")
    subject = Column(String(255), nullable=False, comment="Message subject")
    message = Column(Text, nullable=False, comment="Full message body")
    status = Column(
        String(20), default="open", index=True,
        comment="Ticket status: open | in_progress | resolved | closed"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")

    __table_args__ = (
        Index("idx_contacts_status_created", "status", "created_at"),
    )
