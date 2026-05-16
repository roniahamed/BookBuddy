"""
Password reset token model for the forgot-password flow.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class PasswordResetToken(Base):
    """One-time token for password reset flow (Forgot Password → Verify Code → Set New Password)."""
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), nullable=False, comment="Fernet-encrypted 6-digit OTP code")
    is_used = Column(Boolean, default=False, comment="Marks token as consumed")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="Token expiry timestamp")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
