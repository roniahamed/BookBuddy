"""
Celery tasks — all background and scheduled operations.

Background tasks (called via .delay()):
- send_otp_email_task: Send OTP verification email
- send_push_notification_task: Send FCM push notification
- send_notification_email_task: Send notification email
- translate_and_cache_task: Background translation + Redis caching

Scheduled tasks (Celery Beat):
- check_overdue_books: Every 6 hours — find overdue borrows, notify users
- send_due_date_reminders: Daily — remind users 2 days before due
- cleanup_expired_otps: Daily — delete expired OTP tokens
"""
import logging
from app.background.celery_app import celery_app

# Import all models to ensure SQLAlchemy mappers are fully initialized for Celery tasks
from app.modules.users.model import User, UserSettings, UserFCMToken
from app.modules.auth.model import PasswordResetToken
from app.modules.books.model import Book, Genre, Wishlist, Review
from app.modules.borrowing.model import BorrowRequest
from app.modules.chat.model import Conversation, Message
from app.modules.admin.model import AppConfig

logger = logging.getLogger(__name__)


# ─── Background Tasks (async via .delay()) ──────────────

@celery_app.task(name="app.background.tasks.send_otp_email_task", bind=True, max_retries=3)
def send_otp_email_task(self, to: str, otp_code: str, user_name: str):
    """Send OTP verification email via SMTP (non-blocking)."""
    try:
        from app.core.email import send_otp_email
        result = send_otp_email(to, otp_code, user_name)
        if not result:
            raise Exception("Email send returned False")
        logger.info(f"OTP email sent to {to}")
        return {"status": "sent", "to": to}
    except Exception as e:
        logger.error(f"OTP email task failed: {e}")
        self.retry(exc=e, countdown=30)


@celery_app.task(name="app.background.tasks.send_push_notification_task", bind=True, max_retries=3)
def send_push_notification_task(self, user_id: int, title: str, body: str, data: dict = None):
    """Send FCM push notification to all user devices (non-blocking)."""
    try:
        from app.core.database import SessionLocal
        from app.modules.users.model import UserFCMToken
        from app.core.firebase import send_push_notification
        
        db = SessionLocal()
        try:
            tokens = db.query(UserFCMToken.token).filter(UserFCMToken.user_id == user_id).all()
            token_list = [t[0] for t in tokens]
            
            if not token_list:
                return {"status": "skipped", "reason": "no tokens"}
                
            result = send_push_notification(token_list, title, body, data)
            if not result:
                raise Exception("Push notification returned False")
            logger.info(f"Push notification sent: {title} to {len(token_list)} devices")
            return {"status": "sent", "devices": len(token_list)}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Push notification task failed: {e}")
        self.retry(exc=e, countdown=30)


@celery_app.task(name="app.background.tasks.send_notification_email_task", bind=True, max_retries=3)
def send_notification_email_task(self, to: str, title: str, message: str, user_name: str = "User"):
    """Send notification email (borrow approved, returned, etc.)."""
    try:
        from app.core.email import send_notification_email
        result = send_notification_email(to, title, message, user_name)
        if not result:
            raise Exception("Email send returned False")
        logger.info(f"Notification email sent to {to}: {title}")
        return {"status": "sent", "to": to, "title": title}
    except Exception as e:
        logger.error(f"Notification email task failed: {e}")
        self.retry(exc=e, countdown=30)


@celery_app.task(name="app.background.tasks.translate_and_cache_task")
def translate_and_cache_task(text: str, target_lang: str, cache_key: str):
    """Translate text and cache result in Redis."""
    try:
        import redis
        from app.core.translation import translate_text
        from app.core.config import settings

        translated = translate_text(text, target_lang)

        # Cache in Redis for 24 hours
        r = redis.from_url(settings.REDIS_URL)
        r.setex(cache_key, 86400, translated)

        logger.info(f"Translation cached: {cache_key}")
        return {"status": "cached", "key": cache_key}
    except Exception as e:
        logger.error(f"Translation cache task failed: {e}")
        return {"status": "failed", "error": str(e)}


# ─── Scheduled Tasks (Celery Beat) ──────────────────────

@celery_app.task(name="app.background.tasks.check_overdue_books")
def check_overdue_books():
    """
    Scheduled: Every 6 hours.
    Find active borrows past due_date, send push + email reminders.
    """
    try:
        from datetime import datetime, timezone
        from app.core.database import SessionLocal
        from app.modules.borrowing.model import BorrowRequest
        from app.modules.users.model import User
        from app.modules.books.model import Book

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            overdue = (
                db.query(BorrowRequest)
                .filter(
                    BorrowRequest.status == "active",
                    BorrowRequest.due_date < now,
                )
                .all()
            )

            for borrow in overdue:
                # Notify borrower
                borrower = db.query(User).filter(User.id == borrow.borrower_id).first()
                book = db.query(Book).filter(Book.id == borrow.book_id).first()
                if borrower and book:
                    # Notify borrower
                    send_push_notification_task.delay(
                        borrower.id,
                        "Book Overdue!",
                        f'"{book.title}" is overdue. Please return it as soon as possible.',
                    )
                    # Send email notification
                    if borrower.settings and borrower.settings.email_notifications:
                        send_notification_email_task.delay(
                            borrower.email,
                            "Book Overdue Reminder",
                            f'Your borrowed book "{book.title}" is overdue. Please return it as soon as possible.',
                            borrower.full_name,
                        )

                    # Also notify the book owner
                    owner = db.query(User).filter(User.id == book.owner_id).first()
                    if owner:
                        send_push_notification_task.delay(
                            owner.id,
                            "Book Overdue",
                            f'"{book.title}" lent to {borrower.full_name} is overdue.',
                        )

            logger.info(f"Overdue check complete: {len(overdue)} overdue books found")
            return {"overdue_count": len(overdue)}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Overdue check failed: {e}")
        return {"error": str(e)}


@celery_app.task(name="app.background.tasks.send_due_date_reminders")
def send_due_date_reminders():
    """
    Scheduled: Daily at 9:00 AM UTC.
    Send reminders for books due within the configured reminder window (default: 2 days).
    """
    try:
        from datetime import datetime, timezone, timedelta
        from app.core.database import SessionLocal
        from app.modules.borrowing.model import BorrowRequest
        from app.modules.users.model import User
        from app.modules.books.model import Book
        from app.modules.admin.service import AdminConfigService

        db = SessionLocal()
        try:
            config_service = AdminConfigService(db)
            reminder_days = config_service.get_int("due_date_reminder_days_before", 2)

            now = datetime.now(timezone.utc)
            reminder_start = now
            reminder_end = now + timedelta(days=reminder_days)

            upcoming = (
                db.query(BorrowRequest)
                .filter(
                    BorrowRequest.status == "active",
                    BorrowRequest.due_date.between(reminder_start, reminder_end),
                )
                .all()
            )

            for borrow in upcoming:
                borrower = db.query(User).filter(User.id == borrow.borrower_id).first()
                book = db.query(Book).filter(Book.id == borrow.book_id).first()
                if borrower and book:
                    days_left = (borrow.due_date - now).days
                    # Push notification
                    send_push_notification_task.delay(
                        borrower.id,
                        "Return Reminder",
                        f'"{book.title}" is due in {days_left} day(s). Please plan your return.',
                    )
                    if borrower.settings and borrower.settings.email_notifications:
                        send_notification_email_task.delay(
                            borrower.email,
                            "Return Reminder",
                            f'Your borrowed book "{book.title}" is due in {days_left} day(s). Please plan your return.',
                            borrower.full_name,
                        )

            logger.info(f"Due date reminders sent: {len(upcoming)} books due within {reminder_days} days")
            return {"reminder_count": len(upcoming)}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Due date reminder failed: {e}")
        return {"error": str(e)}


@celery_app.task(name="app.background.tasks.cleanup_expired_otps")
def cleanup_expired_otps():
    """
    Scheduled: Daily at 3:00 AM UTC.
    Delete expired and used OTP tokens from the database.
    """
    try:
        from datetime import datetime, timezone
        from app.core.database import SessionLocal
        from app.modules.auth.model import PasswordResetToken

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            deleted = (
                db.query(PasswordResetToken)
                .filter(
                    (PasswordResetToken.expires_at < now) |
                    (PasswordResetToken.is_used == True)
                )
                .delete(synchronize_session=False)
            )
            db.commit()
            logger.info(f"Cleaned up {deleted} expired/used OTP tokens")
            return {"deleted_count": deleted}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"OTP cleanup failed: {e}")
        return {"error": str(e)}
