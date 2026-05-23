import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app.core.database import SessionLocal
from app.modules.admin.service import AdminManagementService

def main():
    db = SessionLocal()
    service = AdminManagementService(db)
    
    users = service.list_users(page=1, size=5)
    print("Users List Response:")
    print(f"Total Members: {users.total_members}")
    print(f"Total Borrow Requests: {users.total_borrow_requests}")
    print(f"Avg Rating: {users.avg_rating}")
    print("\nItems:")
    for item in users.items:
        print(f" - {item.full_name} ({item.email}): Rating={item.avg_rating}, Borrows={item.borrow_count}, Status={'Active' if item.is_active else 'Suspended'}")

    db.close()

if __name__ == "__main__":
    main()
