"""
AppConfig model — admin-configurable key/value settings stored in DB.
Replaces ALL hardcoded configuration values.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class AppConfig(Base):
    """
    Dynamic application configuration.
    Admin can update these values via API — no code changes or redeployment needed.
    """
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True, comment="Config key, e.g. borrow_reward_borrower_points")
    value = Column(Text, nullable=False, comment="Config value as string (cast in application)")
    description = Column(Text, nullable=True, comment="Human-readable description for admin UI")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ContactMessage(Base):
    """
    Contact form submissions from users.
    """
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ActivityLog(Base):
    """
    Log of platform activities (e.g. book added, borrow requested, review posted).
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User")
