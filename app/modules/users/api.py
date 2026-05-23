"""
Users module API endpoints.

Covers:
- GET    /users/me                          — My full profile (Profile sidebar)
- PATCH  /users/me                          — Update my profile (edit icon)
- GET    /users/me/settings                 — Get settings (Settings screen)
- PATCH  /users/me/settings                 — Update settings
- PATCH  /users/me/security/change-password — Change password (Security screen)
- DELETE /users/me/account                  — Delete account (Security screen)
- GET    /users/{user_id}                   — Public profile (Other People Profile)
- GET    /users/{user_id}/books             — User's uploaded books (public)
- GET    /users/{user_id}/reviews           — Community ratings for user
"""
from fastapi import APIRouter, Depends, status, Request, HTTPException, UploadFile, File, Form
import os
import uuid
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.dependencies import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.users.service import UserService
from app.modules.users.schema import (
    UserProfileResponse, UserUpdateRequest,
    UserPublicProfileResponse,
    UserSettingsResponse, UserSettingsUpdateRequest,
    ChangePasswordRequest, ChangePasswordResponse,
    DeleteAccountResponse,
)
from app.modules.books.service import BookService
from app.modules.books.schema import ReviewPaginatedResponse
from app.shared.pagination import PaginationParams

router = APIRouter()


# ─── My Profile ──────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get my profile",
    description=(
        "Returns the full profile of the authenticated user including stats "
        "(books uploaded, available, borrowed), credits, rating, and notification settings. "
        "Corresponds to the Profile sidebar in the UI."
    ),
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.get_my_profile(current_user)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="Update my profile",
    description=(
        "Update profile fields: name, avatar_file (image upload), location, GPS coordinates. "
        "Only provided fields are updated (partial update). "
        "Corresponds to the edit icon on the Profile sidebar. "
        "Accepts multipart/form-data."
    ),
)
async def update_my_profile(
    request: Request,
    full_name: Optional[str] = Form(None, min_length=2, max_length=150),
    location: Optional[str] = Form(None, max_length=255),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    avatar_file: Optional[UploadFile] = File(None),
    email: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if email is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email cannot be changed. Please contact support for assistance.",
        )
        
    update_data = {}
    if full_name is not None: update_data["full_name"] = full_name
    if location is not None: update_data["location"] = location
    if latitude is not None: update_data["latitude"] = latitude
    if longitude is not None: update_data["longitude"] = longitude
    
    if avatar_file is not None and avatar_file.filename:
        if not avatar_file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Avatar must be an image file")
        ext = avatar_file.filename.split(".")[-1] if "." in avatar_file.filename else "jpg"
        filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join("static/uploads", filename)
        os.makedirs("static/uploads", exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(await avatar_file.read())
        update_data["avatar_url"] = f"/static/uploads/{filename}"

    service = UserService(db)
    updated_user = service.repo.update_user(current_user.id, update_data)
    return service.get_my_profile(updated_user)

# ─── Settings ────────────────────────────────────────────

@router.get(
    "/me/settings",
    response_model=UserSettingsResponse,
    summary="Get my settings",
    description=(
        "Returns notification and language preferences. "
        "Corresponds to the Settings screen with Language (EN/HE), "
        "Email Notification toggle, and New Message Alert toggle."
    ),
)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.get_settings(current_user)


@router.patch(
    "/me/settings",
    response_model=UserSettingsResponse,
    summary="Update my settings",
    description=(
        "Update language and notification preferences. "
        "Only provided fields are updated (partial update)."
    ),
)
async def update_settings(
    data: UserSettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.update_settings(current_user, data)


# ─── Security ────────────────────────────────────────────

@router.patch(
    "/me/security/change-password",
    response_model=ChangePasswordResponse,
    summary="Change password",
    description=(
        "Change the account password. Requires the current password for verification. "
        "New password and confirm password must match. "
        "Corresponds to the Change Password form on the Security screen."
    ),
    responses={
        400: {"description": "Current password incorrect or passwords don't match"},
    },
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.change_password(current_user, data)


@router.delete(
    "/me/account",
    response_model=DeleteAccountResponse,
    summary="Delete my account",
    description=(
        "PERMANENTLY delete the account and all related data (books, borrows, chats, reviews). "
        "This action cannot be undone. "
        "'Once you delete your account, there is no going back. Please be certain.'"
    ),
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.delete_account(current_user)


# ─── Public Profile ──────────────────────────────────────

@router.get(
    "/{user_id}",
    response_model=UserPublicProfileResponse,
    summary="View user's public profile",
    description=(
        "View another user's public profile with their name, email, location, "
        "rating, and stats (Books Uploaded / Available / Borrowed). "
        "Corresponds to the 'Other People Profile' screen."
    ),
    responses={
        404: {"description": "User not found"},
    },
)
async def get_public_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = UserService(db)
    return service.get_public_profile(user_id)


@router.get(
    "/{user_id}/ratings",
    response_model=ReviewPaginatedResponse,
    summary="Get user ratings",
    description=(
        "Get community ratings/reviews for a specific user. "
        "Shown in the 'Community Ratings' tab on the user profile."
    ),
)
async def get_user_ratings(
    user_id: int,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    service = BookService(db)
    return service.get_user_reviews(user_id, pagination)
