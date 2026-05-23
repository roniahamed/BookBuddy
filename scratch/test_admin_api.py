import sys
import os
import asyncio
from datetime import datetime
sys.path.insert(0, os.path.abspath("."))

from app.core.database import SessionLocal, engine, Base
from app.modules.users.model import User
from app.modules.books.model import Book
from app.modules.admin.model import ActivityLog
from app.modules.admin.service import AdminManagementService

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # 1. Ensure a user exists
    user = db.query(User).filter_by(email="admin_test_activity@example.com").first()
    if not user:
        user = User(
            email="admin_test_activity@example.com",
            full_name="Admin Activity Tester",
            role="admin",
            password_hash="fake",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Add an activity directly to test model
    activity = ActivityLog(
        user_id=user.id,
        action_type="test_action",
        description="This is a test activity for the admin dashboard."
    )
    db.add(activity)
    db.commit()
    print("Added test ActivityLog.")

    # 3. Test AdminManagementService
    service = AdminManagementService(db)
    
    stats = service.get_stats()
    print("Stats Response:")
    print(stats)
    
    borrows = service.list_borrows(status=None, page=1, size=5)
    print("\nBorrows Response:")
    print(borrows)

    activities = service.list_activities(page=1, size=5)
    print("\nActivities Response:")
    print(activities)

    db.close()

if __name__ == "__main__":
    main()
