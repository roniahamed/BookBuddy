"""
AppConfig model — admin-configurable key/value settings stored in DB.
Replaces ALL hardcoded configuration values.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
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
