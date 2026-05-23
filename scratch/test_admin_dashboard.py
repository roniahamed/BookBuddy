import os
import sys

# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_db
from app.modules.admin.api import require_admin
from app.modules.users.model import User
from app.core.database import SessionLocal

# Create a test client
client = TestClient(app)

def test_admin_endpoints():
    db = SessionLocal()
    
    # 1. Find an admin user
    admin_user = db.query(User).filter(User.role == "admin").first()
    if not admin_user:
        print("No admin user found. Creating a temporary one...")
        admin_user = User(
            full_name="Test Admin",
            email="testadmin@example.com",
            password_hash="fakehash",
            role="admin",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    
    # Override the require_admin dependency to bypass JWT auth
    app.dependency_overrides[require_admin] = lambda: admin_user
    
    try:
        print("\n--- 1. Testing GET /api/v1/admin/stats ---")
        res = client.get("/api/v1/admin/stats")
        if res.status_code == 200:
            print("✅ Success! Response:")
            print(res.json())
        else:
            print(f"❌ Failed ({res.status_code}):", res.text)
            
        print("\n--- 2. Testing GET /api/v1/admin/users ---")
        res = client.get("/api/v1/admin/users?page=1&size=5")
        if res.status_code == 200:
            print("✅ Success! Metrics:", res.json().get("metrics"))
            print(f"Returned {len(res.json().get('items', []))} users.")
        else:
            print(f"❌ Failed ({res.status_code}):", res.text)

        print("\n--- 3. Testing GET /api/v1/admin/books ---")
        res = client.get("/api/v1/admin/books?page=1&size=5")
        if res.status_code == 200:
            print("✅ Success! Metrics:", res.json().get("metrics"))
            print(f"Returned {len(res.json().get('items', []))} books.")
        else:
            print(f"❌ Failed ({res.status_code}):", res.text)

        print("\n--- 4. Testing GET /api/v1/admin/borrows ---")
        res = client.get("/api/v1/admin/borrows?page=1&size=5")
        if res.status_code == 200:
            print("✅ Success! Items returned:", len(res.json().get("items", [])))
        else:
            print(f"❌ Failed ({res.status_code}):", res.text)
            
        print("\n--- 5. Testing GET /api/v1/admin/activities ---")
        res = client.get("/api/v1/admin/activities?page=1&size=5")
        if res.status_code == 200:
            print("✅ Success! Items returned:", len(res.json().get("items", [])))
        else:
            print(f"❌ Failed ({res.status_code}):", res.text)

    finally:
        # Cleanup
        app.dependency_overrides.clear()
        db.close()

if __name__ == "__main__":
    test_admin_endpoints()
