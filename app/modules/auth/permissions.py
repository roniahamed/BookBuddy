"""
Auth module permissions.
"""
from fastapi import Depends, HTTPException, status
from app.modules.users.model import User
from app.modules.auth.dependencies import get_current_user


async def require_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    return current_user
