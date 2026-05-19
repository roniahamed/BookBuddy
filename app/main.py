"""
BookBuddy API — Main Application Entry Point

Community book-sharing platform backend.
Built with FastAPI, SQLAlchemy, PostgreSQL, Firebase, Celery + Redis.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.core.middleware import setup_middleware
from app.core.logging import setup_logging
from app.core.dependencies import get_db
from app.router import api_router

# ─── Import ALL models so Base.metadata.create_all() creates all tables ───
from app.modules.users.model import User, UserSettings, UserFCMToken
from app.modules.auth.model import PasswordResetToken
from app.modules.books.model import Book, Genre, Wishlist, Review
from app.modules.borrowing.model import BorrowRequest
from app.modules.chat.model import Conversation, Message
from app.modules.admin.model import AppConfig

# 1. Setup Logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — create tables, seed data on startup."""
    Base.metadata.create_all(bind=engine)

    # Seed default genres if they don't exist
    db = next(get_db())
    try:
        existing = db.query(Genre).count()
        if existing == 0:
            default_genres = [
                "Science", "History", "Self-Help", "Fiction",
                "Children's", "Business", "Drama", "Fantasy",
            ]
            for name in default_genres:
                db.add(Genre(name=name))
            db.commit()

        # Seed default admin configs
        from app.modules.admin.service import AdminConfigService
        config_service = AdminConfigService(db)
        config_service.seed_defaults()

    except Exception:
        db.rollback()
    finally:
        db.close()

    yield
    # Shutdown logic


# ─── Tag Metadata for Beautiful Swagger UI ───────────────
tags_metadata = [
    {
        "name": "Authentication",
        "description": "**Register, login, Google Sign-In, and password management.** "
                       "Supports email/password and Google OAuth via Firebase. "
                       "Includes OTP-based forgot-password flow sent via SMTP email.",
    },
    {
        "name": "Users & Profile",
        "description": "**User profile management.** "
                       "View and edit profiles (email is immutable), manage settings, "
                       "change password, and permanently delete account.",
    },
    {
        "name": "Books",
        "description": "**Browse, search, translate, and manage books.** "
                       "Full-text search, genre filtering, proximity-based discovery, "
                       "EN↔HE auto-translation, wishlist, and book CRUD.",
    },
    {
        "name": "Categories",
        "description": "**Book genre categories.** "
                       "Lookup table: Science, History, Fiction, Fantasy, etc.",
    },
    {
        "name": "Reviews & Ratings",
        "description": "**Community ratings system.** "
                       "Submit reviews after completed borrows. "
                       "Reviews automatically update book and user average ratings.",
    },
    {
        "name": "Borrowing",
        "description": "**Book borrowing lifecycle.** "
                       "Request → Approve → Active (countdown) → Return → Confirm. "
                       "Credit rewards are admin-configurable. "
                       "Overdue reminders via Celery Beat + FCM.",
    },
    {
        "name": "Chat & Messaging",
        "description": "**Encrypted messaging between users.** "
                       "All messages are Fernet-encrypted at rest in the database. "
                       "Start conversations, send messages, track read status.",
    },
    {
        "name": "Notifications",
        "description": "**Notification preferences.** "
                       "Toggle email notifications and push alerts. "
                       "FCM push notifications for borrow events and chat messages.",
    },
    {
        "name": "Admin",
        "description": (
            "**Full platform administration — admin role required.**\n\n"
            "- **Config** — Manage platform settings: borrow points, OTP expiry, radius, durations.\n"
            "- **Stats** — Real-time dashboard snapshot: users, books, borrows, reviews, overdue counts.\n"
            "- **User Management** — List, inspect, suspend/reactivate, or permanently delete users. "
            "Suspend sends FCM + email notification to the user.\n"
            "- **Book Management** — List all listings, override availability, or remove policy-violating books. "
            "Owner is notified on removal.\n"
            "- **Reviews & Ratings** — Monitor all reviews, filter by rating range, "
            "delete abusive reviews with automatic avg_rating recalculation.\n"
            "- **Notifications** — Broadcast FCM push + email to all active users or a specific user "
            "via Celery background tasks."
        ),
    },
    {
        "name": "Contact",
        "description": "**Support contact form.** "
                       "Submit inquiries to the BookBuddy team.",
    },
]


app = FastAPI(
    title=" BookBuddy API",
    description=(
        "## Community Book Sharing Platform\n\n"
        "**BookBuddy** connects neighbors through the joy of reading. "
        "Discover, borrow, and share physical books with your local community.\n\n"
        "### Key Features\n"
        "-  **Authentication** — JWT + Google Sign-In via Firebase\n"
        "-  **Book Discovery** — Search, filter, nearby, EN↔HE translation\n"
        "-  **Borrowing** — Full lifecycle with admin-configurable credit rewards\n"
        "-  **Reviews** — Community ratings for trust building\n"
        "- **Chat** — Fernet-encrypted messaging between users\n"
        "-  **Push Notifications** — FCM via Firebase + Celery background tasks\n"
        "-  **Admin** — DB-driven configuration (no hardcoded values)\n\n"
        "### Authentication\n"
        "Most endpoints require a JWT token. Get one via `POST /auth/login` "
        "or `POST /auth/google` and include as `Authorization: Bearer <token>`.\n\n"
        "### Background Infrastructure\n"
        "- **Celery + Redis** — email sending, push notifications, translation caching\n"
        "- **Celery Beat** — overdue reminders, due-date alerts, OTP cleanup\n\n"
        "---\n"
        "*Built with by the BookBuddy team*"
    ),
    version="2.0.0",
    openapi_tags=tags_metadata,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=None,
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "BookBuddy Support",
        "email": "hello@bookbuddy.com",
    },
    license_info={
        "name": "All Rights Reserved (Proprietary)",
    },
)

# 2. Setup Middlewares
setup_middleware(app)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# 3. Include Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# 4. Mount Admin Dashboard (SQLAlchemy Admin)
from app.modules.admin.dashboard import setup_admin
setup_admin(app)

# 5. Mount Static Files for Uploads
from fastapi.staticfiles import StaticFiles
import os
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Custom Swagger UI with Username-to-Email visual override ────
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html_response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Documentation",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_ui_parameters={"persistAuthorization": True},
    )
    
    # Pure-JS visual mapping of 'username' to 'email' using reactive MutationObserver
    js_to_inject = """
    <script>
    const observer = new MutationObserver((mutations) => {
        // Find and swap text inside labels, spans, headers, cells
        const elements = document.querySelectorAll("label, span, th, td");
        elements.forEach(el => {
            if (el.textContent === "username:") {
                el.textContent = "email:";
            }
            if (el.textContent === "username") {
                el.textContent = "email";
            }
        });
        
        // Find and swap input placeholders
        const inputs = document.querySelectorAll("input");
        inputs.forEach(input => {
            if (input.placeholder === "username") {
                input.placeholder = "email";
            }
        });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    </script>
    """
    
    original_body = html_response.body.decode("utf-8")
    modified_body = original_body.replace("</body>", f"{js_to_inject}</body>")
    
    return HTMLResponse(content=modified_body, status_code=html_response.status_code)


# ─── Root & Contact Endpoints ────────────────────────────

@app.get("/", tags=[" Health Check"])
async def root():
    """API health check and welcome message."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "features": [
            "Firebase Google Login",
            "FCM Push Notifications",
            "SMTP OTP Email",
            "Fernet Chat Encryption",
            "Celery + Redis Background Tasks",
            "Google Translate (EN↔HE)",
            "PostgreSQL + Haversine Geo",
            "Admin-Configurable Settings",
        ],
    }


class ContactRequest(BaseModel):
    """Contact form submission (Contact page)."""
    name: str = Field(..., min_length=2, max_length=150, description="Your name")
    email: EmailStr = Field(..., description="Your email address")
    subject: str = Field(..., min_length=2, max_length=255, description="Subject line")
    message: str = Field(..., min_length=10, description="Your message")

    model_config = {"json_schema_extra": {
        "example": {
            "name": "Alex Morgan",
            "email": "alex@example.com",
            "subject": "How can I join the community?",
            "message": "I'd love to learn more about sharing books in my neighborhood.",
        }
    }}


class ContactResponse(BaseModel):
    """Response after submitting contact form."""
    message: str = "Thank you for reaching out! We'll get back to you soon."


@app.post(
    f"{settings.API_V1_STR}/contact",
    response_model=ContactResponse,
    tags=[" Contact"],
    summary="Submit contact form",
    description="Submit an inquiry via the Contact page.",
)
async def submit_contact(data: ContactRequest):
    # Send via Celery background task
    try:
        from app.background.tasks import send_notification_email_task
        send_notification_email_task.delay(
            settings.SMTP_FROM_EMAIL,
            f"Contact Form: {data.subject}",
            f"From: {data.name} ({data.email})\n\n{data.message}",
            "Support Team",
        )
    except Exception:
        pass  # Non-critical
    return ContactResponse()
