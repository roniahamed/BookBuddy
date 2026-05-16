"""
BorrowRequest SQLAlchemy model.
Tracks the full lifecycle of a book loan: pending → approved → active → returned → confirmed.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class BorrowRequest(Base):
    """
    Tracks the full lifecycle of a book loan.
    Powers the Borrowed and Lent Out profile tabs.

    Status flow: pending → approved → active → returned → confirmed | cancelled
    """
    __tablename__ = "borrow_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    borrower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(
        String(30), nullable=False, default="pending", index=True,
        comment="Enum: pending | approved | active | returned | confirmed | cancelled"
    )
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    borrowed_at = Column(DateTime(timezone=True), nullable=True, comment="When book was physically picked up")
    due_date = Column(DateTime(timezone=True), nullable=True, comment="Return deadline")
    returned_at = Column(DateTime(timezone=True), nullable=True, comment="When borrower marked as returned")
    confirmed_at = Column(DateTime(timezone=True), nullable=True, comment="When owner confirmed receipt")

    # Relationships
    book = relationship("Book", back_populates="borrow_requests")
    borrower = relationship("User", back_populates="borrow_requests", foreign_keys=[borrower_id])
    review = relationship("Review", back_populates="borrow_request", uselist=False)

    __table_args__ = (
        Index("idx_borrow_status", "status"),
        Index("idx_borrow_borrower_status", "borrower_id", "status"),
        Index("idx_borrow_book_status", "book_id", "status"),
    )
