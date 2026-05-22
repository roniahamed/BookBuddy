import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from datetime import datetime, timedelta
from jose import jwt

def create_token(user_id: int):
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode = {"sub": str(user_id), "type": "access", "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

admin_token = create_token(1)
user_token = create_token(4)

headers_admin = {"Authorization": f"Bearer {admin_token}"}
headers_user = {"Authorization": f"Bearer {user_token}"}

def print_res(title, res):
    print(f"\n--- {title} ---")
    print(f"Status: {res.status_code}")
    try:
        print(json.dumps(res.json(), indent=2)[:500])
    except:
        print(res.text[:500])

with TestClient(app) as client:
    print("Testing 1. Admin List Contacts")
    res = client.get("/api/v1/admin/contacts?page=1&size=20", headers=headers_admin)
    print_res("Admin List Contacts", res)

    print("Testing 2. User Ratings")
    res = client.get("/api/v1/users/4/ratings?page=1&per_page=20", headers=headers_user)
    print_res("User Ratings", res)

    print("Testing 3. Recommended Books")
    res = client.get("/api/v1/books/recommended?page=1&per_page=20", headers=headers_user)
    print_res("Recommended Books", res)

    print("Testing 4. Cancel Borrow Request")
    # Need to find a pending borrow request for user 4 or just let it fail with 404
    res = client.post("/api/v1/borrow-requests/9999/cancel", headers=headers_user)
    print_res("Cancel Borrow Request", res)

    print("Testing 5. WebSocket Chat")
    try:
        with client.websocket_connect(f"/api/v1/conversations/1/ws?token={user_token}") as websocket:
            websocket.send_text("Hello from test script!")
            data = websocket.receive_text()
            print(f"\n--- WebSocket ---")
            print(f"Received: {data}")
    except Exception as e:
        print(f"WebSocket error: {e}")
