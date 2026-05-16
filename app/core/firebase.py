"""
Firebase Admin SDK initialization.
- Google Login: verify Firebase ID tokens
- FCM: send push notifications
"""
import json
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_app = None


def _init_firebase():
    """Initialize Firebase Admin SDK (lazy, once)."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
    except Exception as e:
        logger.warning(f"Firebase init failed (Google Login + FCM will be disabled): {e}")
        _firebase_app = None

    return _firebase_app


def verify_google_token(id_token: str) -> Optional[dict]:
    """
    Verify a Firebase ID token from Google Sign-In.
    Returns decoded token dict with uid, email, name, picture etc.
    Returns None if verification fails.
    """
    _init_firebase()
    if _firebase_app is None:
        return None

    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(id_token)
        return {
            "uid": decoded.get("uid"),
            "email": decoded.get("email"),
            "name": decoded.get("name", ""),
            "picture": decoded.get("picture"),
            "email_verified": decoded.get("email_verified", False),
        }
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        return None


def send_push_notification(
    fcm_tokens: list[str],
    title: str,
    body: str,
    data: dict = None,
) -> bool:
    """
    Send a push notification via Firebase Cloud Messaging.
    Returns True on success, False on failure.
    """
    if not fcm_tokens:
        return False

    _init_firebase()
    if _firebase_app is None:
        logger.warning("Firebase not initialized, skipping push notification")
        return False

    try:
        from firebase_admin import messaging

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            tokens=fcm_tokens,
        )
        response = messaging.send_each_for_multicast(message)
        logger.info(f"FCM push sent: {response.success_count} success, {response.failure_count} failure")
        return response.success_count > 0
    except Exception as e:
        logger.error(f"FCM push failed: {e}")
        return False
