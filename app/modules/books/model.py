"""
Book, Genre, Wishlist, and Review SQLAlchemy models.
Maps to books, genres, wishlist, and reviews tables from the ERD.
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Genre(Base):
    """Lookup table for book genres. Used for filtering on Browse screen."""
    __tablename__ = "genres"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="e.g. Fiction, Science, History, Fantasy")

    # Relationships
    books = relationship("Book", back_populates="genre")


class Author(Base):
    """Lookup table for book authors."""
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True, comment="Author full name")

    # Relationships
    books = relationship("Book", back_populates="author")


class Book(Base):
    """Physical books listed for community sharing. Uploaded via the Upload Book modal."""
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    genre_id = Column(Integer, ForeignKey("genres.id", ondelete="SET NULL"), nullable=True, index=True)
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False, index=True, comment="Book title")
    description = Column(Text, nullable=True, comment="Description of the book and its condition")
    front_cover_url = Column(String(500), nullable=True, comment="URL to front cover image")
    back_cover_url = Column(String(500), nullable=True, comment="URL to back cover image")
    condition = Column(String(20), nullable=False, default="Good", comment="Enum: New | Good | Used")
    borrow_duration_days = Column(Integer, default=30, comment="Max days allowed to borrow")
    location = Column(String(255), nullable=True, comment="Pickup address for the book")
    latitude = Column(Float, nullable=True, comment="GPS latitude for distance calculation")
    longitude = Column(Float, nullable=True, comment="GPS longitude for distance calculation")
    availability = Column(String(20), default="available", index=True, comment="Enum: available | borrowed | unavailable")
    avg_rating = Column(Float, default=0.00, comment="Computed average from reviews")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="books")
    genre = relationship("Genre", back_populates="books")
    author = relationship("Author", back_populates="books")
    borrow_requests = relationship("BorrowRequest", back_populates="book")
    reviews = relationship("Review", back_populates="book")
    wishlist_entries = relationship("Wishlist", back_populates="book", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_books_title_author", "title", "author_id"),
        Index("idx_books_location", "latitude", "longitude"),
        Index("idx_books_availability", "availability"),
    )


class Wishlist(Base):
    """Many-to-many join for the Wishlist tab on the Profile screen (heart icon)."""
    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="wishlist_items")
    book = relationship("Book", back_populates="wishlist_entries")

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_wishlist_user_book"),
    )


class Review(Base):
    """Community Ratings. Borrowers review lenders; visible on Book Details and user profiles."""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    borrow_request_id = Column(Integer, ForeignKey("borrow_requests.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Float, nullable=False, comment="Star rating, e.g. 4.8 out of 5")
    review_text = Column(Text, nullable=True, comment="Written review body")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    borrow_request = relationship("BorrowRequest", back_populates="review")
    reviewer = relationship("User", back_populates="reviews_written", foreign_keys=[reviewer_id])
    reviewee = relationship("User", back_populates="reviews_received", foreign_keys=[reviewee_id])
    book = relationship("Book", back_populates="reviews")
