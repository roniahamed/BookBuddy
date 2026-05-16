"""
User and UserSettings SQLAlchemy models.
Maps to the users and user_settings tables from the ERD.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """Platform members. Can own books, borrow books, review lenders, and chat."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(150), nullable=False, comment="Display name shown on profile and book cards")
    email = Column(String(255), unique=True, nullable=False, index=True, comment="Used for login and notifications — IMMUTABLE after registration")
    password_hash = Column(String(255), nullable=True, comment="Hashed password (bcrypt). Nullable for Google-auth users")
    avatar_url = Column(String(500), nullable=True, comment="Profile photo URL")
    location = Column(String(255), nullable=True, comment="Street address")
    latitude = Column(Float, nullable=True, comment="GPS latitude for Books Near You feature")
    longitude = Column(Float, nullable=True, comment="GPS longitude for Books Near You feature")
    credits = Column(Integer, default=0, comment="Community coins shown on profile")
    avg_rating = Column(Float, default=0.00, comment="Computed average rating from reviews received")
    role = Column(String(20), default="user", comment="Enum: user | admin")

    # ─── Firebase / Auth Provider fields ─────────────────
    firebase_uid = Column(String(255), nullable=True, unique=True, index=True, comment="Firebase UID for Google-auth users")
    auth_provider = Column(String(20), default="email", comment="Enum: email | google")
    is_active = Column(Boolean, default=True, comment="Whether the user account is active or inactive")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    books = relationship("Book", back_populates="owner", cascade="all, delete-orphan")
    borrow_requests = relationship("BorrowRequest", back_populates="borrower", foreign_keys="BorrowRequest.borrower_id")
    reviews_written = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_id")
    reviews_received = relationship("Review", back_populates="reviewee", foreign_keys="Review.reviewee_id")
    wishlist_items = relationship("Wishlist", back_populates="user", cascade="all, delete-orphan")
    fcm_tokens = relationship("UserFCMToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_location", "latitude", "longitude"),
        Index("idx_users_firebase_uid", "firebase_uid"),
    )


class UserSettings(Base):
    """Per-user notification and language preferences (Settings screen)."""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    language = Column(String(10), default="EN", comment="Preferred UI language, e.g. EN or HE")
    email_notifications = Column(Integer, default=1, comment="Toggle for email notification alerts (1=on, 0=off)")
    new_message_alert = Column(Integer, default=1, comment="Toggle for in-app new message alert (1=on, 0=off)")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="settings")


class UserFCMToken(Base):
    """Stores multiple Firebase Cloud Messaging tokens for users with multiple devices."""
    __tablename__ = "user_fcm_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(Text, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="fcm_tokens")
