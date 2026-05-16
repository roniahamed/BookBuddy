"""
Auth module custom exceptions.
"""
from fastapi import HTTPException, status


class InvalidCredentialsException(HTTPException):
    """Raised when login email or password is incorrect."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


class EmailAlreadyExistsException(HTTPException):
    """Raised when registration email is already taken."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )


class InvalidResetTokenException(HTTPException):
    """Raised when password reset token is invalid or expired."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )


class PasswordMismatchException(HTTPException):
    """Raised when new_password and confirm_password don't match."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match",
        )


class AccountDeactivatedException(HTTPException):
    """Raised when a deactivated account tries to log in."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )
