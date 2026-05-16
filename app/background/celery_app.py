"""
Celery application configuration with Redis broker.
All background and scheduled tasks run through this.
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "bookbuddy",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.background.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ─── Celery Beat Schedule (replaces cron jobs) ──────────
celery_app.conf.beat_schedule = {
    "check-overdue-books": {
        "task": "app.background.tasks.check_overdue_books",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
        "args": (),
    },
    "send-due-date-reminders": {
        "task": "app.background.tasks.send_due_date_reminders",
        "schedule": crontab(minute=0, hour=9),  # Daily at 9:00 AM UTC
        "args": (),
    },
    "cleanup-expired-otps": {
        "task": "app.background.tasks.cleanup_expired_otps",
        "schedule": crontab(minute=0, hour=3),  # Daily at 3:00 AM UTC
        "args": (),
    },
}
