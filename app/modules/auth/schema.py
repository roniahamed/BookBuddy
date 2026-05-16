"""
Auth module Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# ─── Registration ────────────────────────────────────────
class RegisterRequest(BaseModel):
    """Sign In screen: Create an Account form."""
    full_name: str = Field(..., min_length=2, max_length=150, description="Display name", examples=["Alex Morgan"])
    email: EmailStr = Field(..., description="Email address", examples=["alex@example.com"])
    password: str = Field(..., min_length=8, max_length=128, description="Account password")

    model_config = {"json_schema_extra": {
        "example": {
            "full_name": "Alex Morgan",
            "email": "alex@example.com",
            "password": "SecurePass1"
        }
    }}


class RegisterResponse(BaseModel):
    """Response after successful registration."""
    id: int
    full_name: str
    email: str
    message: str = "Account created successfully"


# ─── Login ───────────────────────────────────────────────
class LoginRequest(BaseModel):
    """Log In screen: Email + Password form."""
    email: EmailStr = Field(..., description="Registered email", examples=["alex@example.com"])
    password: str = Field(..., description="Account password")

    model_config = {"json_schema_extra": {
        "example": {
            "email": "alex@example.com",
            "password": "SecurePass1"
        }
    }}


class TokenResponse(BaseModel):
    """JWT token response after successful login."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: "UserBrief"


class UserBrief(BaseModel):
    """Minimal user info returned with token."""
    id: int
    full_name: str
    email: str
    avatar_url: Optional[str] = None
    auth_provider: str = "email"

    model_config = {"from_attributes": True}


# ─── Google Login ────────────────────────────────────────
class GoogleLoginRequest(BaseModel):
    """Google Sign-In: submit Firebase ID token."""
    id_token: str = Field(..., description="Firebase ID token from Google Sign-In")

    model_config = {"json_schema_extra": {
        "example": {"id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6..."}
    }}


# ─── FCM Token ──────────────────────────────────────────
class UpdateFCMTokenRequest(BaseModel):
    """Update FCM push notification token."""
    fcm_token: str = Field(..., description="Firebase Cloud Messaging device token")


class UpdateFCMTokenResponse(BaseModel):
    """Response after updating FCM token."""
    message: str = "FCM token updated successfully"


# ─── Password Reset Flow ────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    """Forgot Password screen: submit email to receive OTP code via SMTP email."""
    email: EmailStr = Field(..., description="Registered email address")


class ForgotPasswordResponse(BaseModel):
    """Response after requesting password reset."""
    message: str = "If this email is registered, a verification code has been sent."


class VerifyCodeRequest(BaseModel):
    """Verify Code screen: submit 6-digit OTP verification code."""
    email: EmailStr = Field(..., description="Email used for reset")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code", examples=["482906"])


class VerifyCodeResponse(BaseModel):
    """Response after code verification."""
    message: str = "Code verified successfully"
    reset_token: str = Field(..., description="Temporary token to use for password reset")


class ResetPasswordRequest(BaseModel):
    """Set New Password screen: new password with reset token."""
    email: EmailStr = Field(..., description="Email used for reset")
    reset_token: str = Field(..., description="Token from verify-code step")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")


class ResetPasswordResponse(BaseModel):
    """Response after successful password reset."""
    message: str = "Password reset successfully. Please log in with your new password."


# ─── Current User ────────────────────────────────────────
class CurrentUserResponse(BaseModel):
    """Full current user info from /auth/me endpoint."""
    id: int
    full_name: str
    email: str
    avatar_url: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    credits: int = 0
    avg_rating: float = 0.0
    role: str = "user"
    auth_provider: str = "email"

    model_config = {"from_attributes": True}


# Rebuild TokenResponse to resolve forward reference
TokenResponse.model_rebuild()
