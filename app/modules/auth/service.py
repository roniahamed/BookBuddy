"""
Auth module service — business logic for authentication flows.
- Email/Password registration & login
- Google Login via Firebase ID token
- SMTP email OTP for password reset
- FCM token management
"""
from sqlalchemy.orm import Session
from app.core.security import create_access_token, create_refresh_token, verify_password, get_password_hash
from app.core.firebase import verify_google_token
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schema import (
    RegisterRequest, RegisterResponse, LoginRequest, TokenResponse,
    UserBrief, ForgotPasswordRequest, ForgotPasswordResponse,
    VerifyCodeRequest, VerifyCodeResponse, ResetPasswordRequest, ResetPasswordResponse,
    GoogleLoginRequest, UpdateFCMTokenRequest, UpdateFCMTokenResponse,
    RefreshTokenResponse,
)
from app.modules.auth.exceptions import (
    InvalidCredentialsException, EmailAlreadyExistsException,
    InvalidResetTokenException, PasswordMismatchException,
    AccountDeactivatedException,
)
from app.modules.admin.service import AdminConfigService
from fastapi import HTTPException


class AuthService:
    """Handles authentication business logic."""

    def __init__(self, db: Session):
        self.repo = AuthRepository(db)
        self.db = db

    def register(self, data: RegisterRequest) -> RegisterResponse:
        """
        Register a new user account.
        - Checks email uniqueness
        - Hashes password
        - Creates user + default settings in single transaction
        """
        if self.repo.email_exists(data.email):
            raise EmailAlreadyExistsException()

        password_hash = get_password_hash(data.password)
        user = self.repo.create_user(
            full_name=data.full_name,
            email=data.email,
            password_hash=password_hash,
            auth_provider="email",
        )
        return RegisterResponse(id=user.id, full_name=user.full_name, email=user.email)

    def login(self, data: LoginRequest) -> TokenResponse:
        """
        Authenticate user with email + password.
        Returns JWT access token.
        """
        user = self.repo.get_user_by_email(data.email)
        if not user:
            raise InvalidCredentialsException()

        if user.auth_provider == "google" and not user.password_hash:
            raise HTTPException(
                status_code=400,
                detail="This account uses Google Sign-In. Please login with Google."
            )

        if not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsException()

        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserBrief(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                avatar_url=user.avatar_url,
                auth_provider=user.auth_provider,
            ),
        )

    def google_login(self, data: GoogleLoginRequest) -> TokenResponse:
        """
        Login or register via Firebase Google Sign-In.
        - Verifies Firebase ID token
        - If user exists (by firebase_uid or email), logs in
        - If new user, registers automatically
        """
        decoded = verify_google_token(data.id_token)
        if not decoded:
            raise HTTPException(status_code=401, detail="Invalid Google token")

        uid = decoded["uid"]
        email = decoded.get("email", "")
        name = decoded.get("name", "Google User")
        picture = decoded.get("picture")

        # Check if user exists by Firebase UID
        user = self.repo.get_user_by_firebase_uid(uid)

        if not user:
            # Check if email already registered (link accounts)
            user = self.repo.get_user_by_email(email)
            if user:
                # Link existing email account to Google
                from app.modules.users.model import User
                self.db.query(User).filter(User.id == user.id).update({
                    "firebase_uid": uid,
                    "auth_provider": "google",
                    "avatar_url": user.avatar_url or picture,
                })
                self.db.commit()
                self.db.refresh(user)
            else:
                # Create new user from Google
                user = self.repo.create_user(
                    full_name=name,
                    email=email,
                    password_hash=None,
                    auth_provider="google",
                    firebase_uid=uid,
                    avatar_url=picture,
                )

        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserBrief(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                avatar_url=user.avatar_url,
                auth_provider=user.auth_provider,
            ),
        )

    def update_fcm_token(self, user, data: UpdateFCMTokenRequest) -> UpdateFCMTokenResponse:
        """Update the user's FCM push notification token."""
        self.repo.update_fcm_token(user.id, data.fcm_token)
        return UpdateFCMTokenResponse()

    def forgot_password(self, data: ForgotPasswordRequest) -> ForgotPasswordResponse:
        """
        Initiate password reset flow.
        Generates 6-digit OTP, encrypts and stores in DB, sends via SMTP email.
        Always returns success to prevent email enumeration.
        """
        user = self.repo.get_user_by_email(data.email)
        if user:
            # Read OTP expiry from admin config
            config_service = AdminConfigService(self.db)
            otp_expiry = config_service.get_int("otp_expiry_minutes", 15)

            code = self.repo.create_reset_token(user.id, expiry_minutes=otp_expiry)

            # Send OTP via Celery background task
            try:
                from app.background.tasks import send_otp_email_task
                send_otp_email_task.delay(user.email, code, user.full_name)
            except Exception:
                # Fallback to direct send if Celery is not available
                from app.core.email import send_otp_email
                send_otp_email(user.email, code, user.full_name)

        return ForgotPasswordResponse()

    def verify_code(self, data: VerifyCodeRequest) -> VerifyCodeResponse:
        """
        Verify the 6-digit OTP code.
        Decrypts stored codes and compares.
        Returns a temporary reset token for the next step.
        """
        token = self.repo.verify_reset_token(data.email, data.code)
        if not token:
            raise InvalidResetTokenException()

        return VerifyCodeResponse(reset_token=str(token.id))

    def reset_password(self, data: ResetPasswordRequest) -> ResetPasswordResponse:
        """
        Set new password using the reset token.
        Validates password match and token validity.
        """
        if data.new_password != data.confirm_password:
            raise PasswordMismatchException()

        user = self.repo.get_user_by_email(data.email)
        if not user:
            raise InvalidResetTokenException()

        # Find valid token by ID
        try:
            token_id = int(data.reset_token)
        except ValueError:
            raise InvalidResetTokenException()

        from app.modules.auth.model import PasswordResetToken
        from datetime import datetime, timezone
        token = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.id == token_id,
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        ).first()

        if not token:
            raise InvalidResetTokenException()

        password_hash = get_password_hash(data.new_password)
        self.repo.update_password(user.id, password_hash)
        self.repo.mark_token_used(token.id)

        return ResetPasswordResponse()

    def refresh_token(self, refresh_token: str) -> RefreshTokenResponse:
        """
        Validate refresh token, check user status, and issue a fresh access and refresh token.
        """
        from jose import jwt, JWTError
        from app.core.config import settings
        
        credentials_exception = HTTPException(
            status_code=401,
            detail="Could not validate refresh credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")
            if user_id is None:
                raise credentials_exception
            if token_type != "refresh":
                raise credentials_exception
        except JWTError:
            raise credentials_exception
            
        user = self.repo.get_user_by_id(int(user_id))
        if user is None or not user.is_active:
            raise credentials_exception
            
        new_access_token = create_access_token(subject=user.id)
        new_refresh_token = create_refresh_token(subject=user.id)
        
        return RefreshTokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )
