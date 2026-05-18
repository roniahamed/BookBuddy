"""
Central API router — includes all module routers with proper prefixes and tags.
"""
from fastapi import APIRouter
from app.modules.auth.api import router as auth_router
from app.modules.users.api import router as users_router
from app.modules.books.api import router as books_router, review_router, genre_router
from app.modules.borrowing.api import router as borrowing_router
from app.modules.chat.api import router as chat_router
from app.modules.notification.api import router as notification_router
from app.modules.admin.api import router as admin_router

api_router = APIRouter()

# ─── Auth Module ─────────────────────────────────────────
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
)

# ─── Users Module ────────────────────────────────────────
api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Users & Profile"],
)

# ─── Books Module ────────────────────────────────────────
api_router.include_router(
    books_router,
    prefix="/books",
    tags=["Books"],
)

# ─── Genres ──────────────────────────────────────────────
api_router.include_router(
    genre_router,
    prefix="/genres",
    tags=["Categories"],
)

# ─── Reviews ─────────────────────────────────────────────
api_router.include_router(
    review_router,
    prefix="/reviews",
    tags=["Reviews & Ratings"],
)

# ─── Borrowing Module ────────────────────────────────────
api_router.include_router(
    borrowing_router,
    prefix="/borrow-requests",
    tags=["Borrowing"],
)

# ─── Chat Module ─────────────────────────────────────────
api_router.include_router(
    chat_router,
    prefix="/conversations",
    tags=["Chat & Messaging"],
)

# ─── Notification Module ─────────────────────────────────
api_router.include_router(
    notification_router,
    prefix="/notifications",
    tags=["Notifications"],
)

# ─── Admin Module ─────────────────────────────────────────
api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["Admin"],
)
