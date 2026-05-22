import requests
import json
import sys
import os
from datetime import datetime, timedelta
from jose import jwt

# Generate tokens
SECRET_KEY = "yoursupersecretkeyhere"
ALGORITHM = "HS256"

def create_token(user_id: int):
    expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode = {"sub": str(user_id), "type": "access", "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def print_res(title, res):
    print(f"\n--- {title} ---")
    print(f"Status: {res.status_code}")
    try:
        print(json.dumps(res.json(), indent=2)[:500] + ("..." if len(json.dumps(res.json())) > 500 else ""))
    except:
        print(res.text[:500])

BASE_URL = "http://localhost:8001/api/v1"

admin_token = create_token(1)
user_token = create_token(4)

headers_admin = {"Authorization": f"Bearer {admin_token}"}
headers_user = {"Authorization": f"Bearer {user_token}"}

# 1. Test Admin Contacts API
res = requests.get(f"{BASE_URL}/admin/contacts?page=1&size=20", headers=headers_admin)
print_res("Admin List Contacts", res)

# 2. Test User Ratings API
res = requests.get(f"{BASE_URL}/users/4/ratings?page=1&per_page=20", headers=headers_user)
print_res("User Ratings", res)

# 3. Test Recommended Books API
res = requests.get(f"{BASE_URL}/books/recommended?page=1&per_page=20", headers=headers_user)
print_res("Recommended Books", res)

# 4. Test WebSocket Chat
import websockets
import asyncio

async def test_ws():
    print("\n--- Testing WebSocket ---")
    uri = f"ws://localhost:8001/api/v1/conversations/1/ws?token={user_token}"
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket Connected successfully!")
            await websocket.send("Hello from test script!")
            print("Sent message")
            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            print(f"Received via WebSocket: {response[:200]}")
    except Exception as e:
        print(f"WebSocket error: {e}")

asyncio.run(test_ws())
