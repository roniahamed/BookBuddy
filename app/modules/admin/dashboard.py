from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.core.database import engine, SessionLocal
from app.modules.users.model import User, UserSettings, UserFCMToken
from app.modules.books.model import Book, Genre, Review
from app.modules.borrowing.model import BorrowRequest
from app.modules.chat.model import Message
from app.modules.admin.model import AppConfig
from app.core.security import verify_password
from app.core.config import settings

# ─── Secure Authentication Backend for SQLAdmin ───────────────────

class AdminAuthBackend(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")
        
        if not email or not password:
            return False
            
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user or user.role != "admin" or not user.is_active:
                return False
            
            if not user.password_hash or not verify_password(password, user.password_hash):
                return False
                
            # Logged in successfully: update cookie session
            request.session.update({"token": "admin_auth_token", "admin_email": email})
            return True
        finally:
            db.close()

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        return True

authentication_backend = AdminAuthBackend(secret_key=settings.SECRET_KEY)

# ─── ModelViews for SQLAdmin ──────────────────────────────────────

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.full_name, User.email, User.role, User.is_active, User.created_at]
    column_searchable_list = [User.full_name, User.email]
    column_filters = [User.role, User.is_active]
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    async def on_model_change(self, data: dict, model: User, is_created: bool, request: Request) -> None:
        if "is_active" in data and not data["is_active"]:
            admin_email = request.session.get("admin_email")
            if admin_email and model.email == admin_email:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")

class UserSettingsAdmin(ModelView, model=UserSettings):
    column_list = [UserSettings.user_id, UserSettings.language, UserSettings.email_notifications, UserSettings.new_message_alert]
    name = "User Settings"
    name_plural = "User Settings"
    icon = "fa-solid fa-gear"

class UserFCMTokenAdmin(ModelView, model=UserFCMToken):
    column_list = [UserFCMToken.id, UserFCMToken.user_id, UserFCMToken.token, UserFCMToken.created_at]
    name = "FCM Token"
    name_plural = "FCM Tokens"
    icon = "fa-solid fa-bell"

class BookAdmin(ModelView, model=Book):
    column_list = [Book.id, Book.title, Book.author_id, Book.owner_id, Book.availability, Book.created_at]
    column_searchable_list = [Book.title]
    column_filters = [Book.availability]
    name = "Book"
    name_plural = "Books"
    icon = "fa-solid fa-book"

class GenreAdmin(ModelView, model=Genre):
    column_list = [Genre.id, Genre.name]
    column_searchable_list = [Genre.name]
    name = "Category"
    name_plural = "Categories"
    icon = "fa-solid fa-list"

class BorrowRequestAdmin(ModelView, model=BorrowRequest):
    column_list = [BorrowRequest.id, BorrowRequest.book_id, BorrowRequest.borrower_id, BorrowRequest.status, BorrowRequest.requested_at, BorrowRequest.due_date]
    column_filters = [BorrowRequest.status]
    name = "Borrow Request"
    name_plural = "Borrow Requests"
    icon = "fa-solid fa-handshake"

class ReviewAdmin(ModelView, model=Review):
    column_list = [Review.id, Review.book_id, Review.reviewer_id, Review.rating, Review.created_at]
    column_filters = [Review.rating]
    name = "Review"
    name_plural = "Reviews & Ratings"
    icon = "fa-solid fa-star"

class MessageAdmin(ModelView, model=Message):
    column_list = [Message.id, Message.sender_id, Message.conversation_id, Message.is_read, Message.sent_at]
    column_filters = [Message.is_read]
    name = "Message"
    name_plural = "Messages"
    icon = "fa-solid fa-comment"

class AppConfigAdmin(ModelView, model=AppConfig):
    column_list = [AppConfig.key, AppConfig.value, AppConfig.description]
    column_searchable_list = [AppConfig.key]
    name = "System Setting"
    name_plural = "System Settings"
    icon = "fa-solid fa-sliders"

def setup_admin(app):
    """Initializes and registers SQLAlchemy Admin dashboard to FastAPI app."""
    admin = Admin(
        app, engine, 
        title="BookBuddy Admin Panel", 
        logo_url="https://fastapi.tiangolo.com/img/favicon.png",
        authentication_backend=authentication_backend
    )
    admin.add_view(UserAdmin)
    admin.add_view(UserSettingsAdmin)
    admin.add_view(UserFCMTokenAdmin)
    admin.add_view(BookAdmin)
    admin.add_view(GenreAdmin)
    admin.add_view(BorrowRequestAdmin)
    admin.add_view(ReviewAdmin)
    admin.add_view(MessageAdmin)
    admin.add_view(AppConfigAdmin)
    return admin
