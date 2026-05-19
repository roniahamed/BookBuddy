"""
Auth module dependencies — JWT token decoding and current user resolution.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.dependencies import get_db
from app.modules.auth.repository import AuthRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Decode JWT token → fetch user from DB.
    Used as a dependency for all authenticated endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None:
            raise credentials_exception
        if token_type and token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    repo = AuthRepository(db)
    user = repo.get_user_by_id(int(user_id))

    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(
    token: str | None = Depends(OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)),
    db: Session = Depends(get_db),
):
    """
    Optional authentication — returns user if token is valid, None otherwise.
    Used for endpoints that work with or without auth (e.g., browse books).
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None:
            return None
        if token_type and token_type != "access":
            return None
    except JWTError:
        return None

    repo = AuthRepository(db)
    user = repo.get_user_by_id(int(user_id))
    return user


async def get_current_user_ws(token: str, db: Session):
    """
    WebSocket authentication — returns user if token is valid, None otherwise.
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if user_id is None:
            return None
        if token_type and token_type != "access":
            return None
    except JWTError:
        return None

    repo = AuthRepository(db)
    user = repo.get_user_by_id(int(user_id))
    return user
