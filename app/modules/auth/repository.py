"""
Auth module repository — database operations for authentication.
OTP codes are encrypted in DB using Fernet.
"""
from datetime import datetime, timedelta, timezone
import random
import string
from sqlalchemy.orm import Session, joinedload
from app.modules.users.model import User, UserSettings
from app.modules.auth.model import PasswordResetToken
from app.core.encryption import encrypt, decrypt


class AuthRepository:
    """Handles all auth-related database queries."""

    def __init__(self, db: Session):
        self.db = db

    # ─── User Lookup ─────────────────────────────────────
    def get_user_by_email(self, email: str) -> User | None:
        """Find user by email (case-insensitive). Eager loads settings."""
        return (
            self.db.query(User)
            .options(joinedload(User.settings))
            .filter(User.email == email.lower())
            .first()
        )

    def get_user_by_id(self, user_id: int) -> User | None:
        """Find user by ID. Eager loads settings."""
        return (
            self.db.query(User)
            .options(joinedload(User.settings))
            .filter(User.id == user_id)
            .first()
        )

    def get_user_by_firebase_uid(self, firebase_uid: str) -> User | None:
        """Find user by Firebase UID (for Google login)."""
        return (
            self.db.query(User)
            .options(joinedload(User.settings))
            .filter(User.firebase_uid == firebase_uid)
            .first()
        )

    def email_exists(self, email: str) -> bool:
        """Check if email is already registered (optimized: EXISTS query)."""
        return self.db.query(
            self.db.query(User).filter(User.email == email.lower()).exists()
        ).scalar()

    # ─── User Creation ───────────────────────────────────
    def create_user(
        self,
        full_name: str,
        email: str,
        password_hash: str = None,
        auth_provider: str = "email",
        firebase_uid: str = None,
        avatar_url: str = None,
    ) -> User:
        """Create new user with default settings. Single transaction."""
        user = User(
            full_name=full_name,
            email=email.lower().strip(),
            password_hash=password_hash,
            auth_provider=auth_provider,
            firebase_uid=firebase_uid,
            avatar_url=avatar_url,
        )
        self.db.add(user)
        self.db.flush()  # Get user.id before creating settings

        # Create default settings (1:1 with user)
        settings = UserSettings(user_id=user.id)
        self.db.add(settings)
        self.db.commit()
        self.db.refresh(user)
        return user

    # ─── FCM Token ───────────────────────────────────────
    def update_fcm_token(self, user_id: int, fcm_token: str) -> None:
        """Add user's FCM push notification token to UserFCMToken table."""
        from app.modules.users.model import UserFCMToken
        # Remove this token if it belongs to someone else
        self.db.query(UserFCMToken).filter(UserFCMToken.token == fcm_token, UserFCMToken.user_id != user_id).delete()
        
        # Add to user if it doesn't already exist
        existing = self.db.query(UserFCMToken).filter(UserFCMToken.token == fcm_token, UserFCMToken.user_id == user_id).first()
        if not existing:
            new_token = UserFCMToken(user_id=user_id, token=fcm_token)
            self.db.add(new_token)
            self.db.commit()

    # ─── Password Reset Tokens (OTP encrypted in DB) ────
    def create_reset_token(self, user_id: int, expiry_minutes: int = 15) -> str:
        """Generate 6-digit OTP, encrypt and store in DB, return the plaintext code."""
        # Invalidate any existing unused tokens
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.is_used == False
        ).update({"is_used": True})

        code = ''.join(random.choices(string.digits, k=6))
        # Encrypt the OTP before storing in DB
        encrypted_code = encrypt(code)

        token = PasswordResetToken(
            user_id=user_id,
            token=encrypted_code,  # stored encrypted
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )
        self.db.add(token)
        self.db.commit()
        return code  # return plaintext to send via email

    def verify_reset_token(self, email: str, code: str) -> PasswordResetToken | None:
        """Verify OTP code: decrypt stored tokens and compare."""
        user = self.get_user_by_email(email)
        if not user:
            return None

        # Get all valid (unused, not expired) tokens for this user
        tokens = (
            self.db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.is_used == False,
                PasswordResetToken.expires_at > datetime.now(timezone.utc),
            )
            .all()
        )

        # Decrypt each token and compare with the provided code
        for token in tokens:
            decrypted_code = decrypt(token.token)
            if decrypted_code == code:
                return token

        return None

    def mark_token_used(self, token_id: int) -> None:
        """Mark a reset token as consumed."""
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.id == token_id
        ).update({"is_used": True})
        self.db.commit()

    def update_password(self, user_id: int, password_hash: str) -> None:
        """Update user password hash."""
        self.db.query(User).filter(User.id == user_id).update(
            {"password_hash": password_hash}
        )
        self.db.commit()
