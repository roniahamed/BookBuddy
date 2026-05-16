"""
Fernet encryption utilities for sensitive data.
Used for: chat message bodies, OTP codes in password_reset_tokens.
"""
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
import base64
import hashlib

_fernet = None


def _get_fernet() -> Fernet:
    """Lazy-init Fernet cipher from ENCRYPTION_KEY."""
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPTION_KEY
        if not key or key == "your-fernet-32-byte-base64-key-here":
            # Generate a deterministic key from SECRET_KEY as fallback
            digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            key = base64.urlsafe_b64encode(digest).decode()
        else:
            # Ensure the key is valid Fernet format (32 url-safe base64 bytes)
            try:
                base64.urlsafe_b64decode(key)
            except Exception:
                digest = hashlib.sha256(key.encode()).digest()
                key = base64.urlsafe_b64encode(digest).decode()
        _fernet = Fernet(key)
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a string → base64-encoded ciphertext string."""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext → plaintext string."""
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # If decryption fails (data was stored before encryption was enabled),
        # return the raw value as-is
        return ciphertext
