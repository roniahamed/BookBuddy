#!/usr/bin/env python
import os
import sys

# Add the parent directory to python path so we can import the `app` package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from sqlalchemy.orm import Session
    from app.core.database import SessionLocal
    
    # Import ALL models to register them with SQLAlchemy Base metadata and resolve relationships
    from app.modules.users.model import User, UserSettings, UserFCMToken
    from app.modules.auth.model import PasswordResetToken
    from app.modules.books.model import Book, Genre, Wishlist, Review
    from app.modules.borrowing.model import BorrowRequest
    from app.modules.chat.model import Conversation, Message
    from app.modules.admin.model import AppConfig
    
    from app.core.security import get_password_hash
except ImportError as e:
    print(f"\033[91mError: Could not import app modules. Please make sure you have activated your virtual environment.\033[0m")
    print(f"Details: {e}")
    sys.exit(1)


def create_or_upgrade_superadmin():
    print("\033[94m" + "="*50)
    print("      BookBuddy Superadmin Creator/Upgrader")
    print("="*50 + "\033[0m")

    # Get input from user
    email = input("Enter email address: ").strip().lower()
    if not email:
        print("\033[91mError: Email cannot be empty.\033[0m")
        return

    db: Session = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()

        if existing_user:
            print(f"\nUser with email \033[93m{email}\033[0m already exists (Current Role: \033[93m{existing_user.role}\033[0m).")
            confirm = input("Would you like to upgrade this user to admin role? (y/n): ").strip().lower()
            if confirm == 'y':
                existing_user.role = "admin"
                db.commit()
                print(f"\n\033[92mSuccess: User '{existing_user.full_name}' upgraded to 'admin' role! \033[0m")
            else:
                print("\nOperation cancelled.")
            return

        # If user does not exist, prompt for name and password
        full_name = input("Enter full name: ").strip()
        if not full_name:
            print("\033[91mError: Full name cannot be empty.\033[0m")
            return

        password = input("Enter password: ").strip()
        if not password or len(password) < 3:
            print("\033[91mError: Password must be at least 3 characters long.\033[0m")
            return

        confirm_password = input("Confirm password: ").strip()
        if password != confirm_password:
            print("\033[91mError: Passwords do not match.\033[0m")
            return

        print("\nCreating superadmin...")
        # Hash password
        pwd_hash = get_password_hash(password)

        # Create user
        new_admin = User(
            full_name=full_name,
            email=email,
            password_hash=pwd_hash,
            role="admin",
            auth_provider="email",
            is_active=True,
            credits=100  # Give some default credits for testing
        )
        db.add(new_admin)
        db.flush()  # Generate the user ID

        # Create default user settings
        new_settings = UserSettings(user_id=new_admin.id)
        db.add(new_settings)

        db.commit()
        print(f"\n\033[92mSuccess: Superadmin '{full_name}' ({email}) created successfully with role 'admin'! \033[0m")

    except Exception as e:
        db.rollback()
        print(f"\n\033[91mError creating superadmin: {e}\033[0m")
    finally:
        db.close()


if __name__ == "__main__":
    create_or_upgrade_superadmin()
