"""
Auth module API endpoints.

Covers:
- POST /auth/register          — Create account (Sign In screen)
- POST /auth/login             — Email + password login (Log In screen)
- POST /auth/google            — Google Sign-In via Firebase ID token
- POST /auth/forgot-password   — Request OTP code via SMTP email
- POST /auth/verify-code       — Verify 6-digit OTP code
- POST /auth/reset-password    — Set new password (OTP-verified)
- GET  /auth/me                — Get current authenticated user
- PUT  /auth/fcm-token         — Update FCM push notification token
"""
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.modules.auth.service import AuthService
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schema import (
    RegisterRequest, RegisterResponse,
    LoginRequest, TokenResponse,
    GoogleLoginRequest,
    ForgotPasswordRequest, ForgotPasswordResponse,
    VerifyCodeRequest, VerifyCodeResponse,
    ResetPasswordRequest, ResetPasswordResponse,
    CurrentUserResponse,
    UpdateFCMTokenRequest, UpdateFCMTokenResponse,
    RefreshTokenRequest, RefreshTokenResponse,
)
from app.modules.users.model import User

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
    description=(
        "Register a new user on the BookBuddy platform. "
        "Requires full name, email, and a strong password (min 8 chars). "
        "Automatically creates default notification settings for the user."
    ),
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation error (invalid email or weak password)"},
    },
)
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in to your account",
    description=(
        "Authenticate with email and password. Supports both application/json (email/password) "
        "and application/x-www-form-urlencoded (username/password for Swagger UI authorization)."
    ),
    responses={
        401: {"description": "Invalid email or password"},
    },
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string", "format": "email", "example": "alex@example.com"},
                            "password": {"type": "string", "example": "SecurePass1"}
                        },
                        "required": ["email", "password"]
                    }
                }
            },
            "required": True
        }
    }
)
async def login(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    email = None
    password = None

    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        email = form_data.get("username")
        password = form_data.get("password")
    else:
        try:
            body = await request.json()
            email = body.get("email")
            password = body.get("password")
        except Exception:
            pass

    if not email or not password:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Email and password are required. For Swagger login, enter email in the username field."
        )

    data = LoginRequest(email=email, password=password)
    service = AuthService(db)
    return service.login(data)


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token and rotated refresh token.",
    responses={
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token_endpoint(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.refresh_token(data.refresh_token)


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Google Sign-In",
    description=(
        "Login or register using Google Sign-In. "
        "Submit the Firebase ID token obtained from the client-side Google auth flow. "
        "If the user is new, an account is created automatically. "
        "If the email already exists, the accounts are linked."
    ),
    responses={
        401: {"description": "Invalid Google token"},
    },
)
async def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.google_login(data)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request password reset OTP",
    description=(
        "Submit your registered email to receive a 6-digit OTP code via SMTP email. "
        "The OTP is encrypted before storage in the database. "
        "The response is always the same to prevent email enumeration attacks."
    ),
)
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.forgot_password(data)


@router.post(
    "/verify-code",
    response_model=VerifyCodeResponse,
    summary="Verify OTP code",
    description=(
        "Verify the 6-digit OTP code received via email. "
        "The code is decrypted from the database and validated. "
        "Returns a temporary reset token to use in the next step."
    ),
    responses={
        400: {"description": "Invalid or expired verification code"},
    },
)
async def verify_code(data: VerifyCodeRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.verify_code(data)


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Set new password",
    description=(
        "Set a new password using the reset token obtained from the verify-code step. "
        "Both new_password and confirm_password must match."
    ),
    responses={
        400: {"description": "Invalid reset token or passwords don't match"},
    },
)
async def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.reset_password(data)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Get current user profile",
    description="Returns the full profile of the currently authenticated user.",
    responses={
        401: {"description": "Not authenticated or invalid token"},
    },
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put(
    "/fcm-token",
    response_model=UpdateFCMTokenResponse,
    summary="Update FCM push notification token",
    description=(
        "Update the device's Firebase Cloud Messaging token for push notifications. "
        "Call this after each app login or when the token refreshes."
    ),
)
async def update_fcm_token(
    data: UpdateFCMTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    return service.update_fcm_token(current_user, data)
