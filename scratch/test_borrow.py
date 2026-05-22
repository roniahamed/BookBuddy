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
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

user_token = create_token(4) # Assuming borrower
owner_token = create_token(1) # Assuming owner of book 1

headers_user = {"Authorization": f"Bearer {user_token}"}
headers_owner = {"Authorization": f"Bearer {owner_token}"}

with TestClient(app) as client:
    # 1. User 4 requests to borrow book 1
    # First, make sure book 1 is available. Let's assume it is or we use book 9 which we saw in recommended
    res = client.post("/api/v1/borrow-requests", json={"book_id": 9, "message": "I want this!"}, headers=headers_user)
    print("Create Borrow Request:")
    print(res.status_code, res.json())
    
    if res.status_code == 201:
        req_id = res.json()["id"]
        # 2. User 4 cancels the request
        res_cancel = client.post(f"/api/v1/borrow-requests/{req_id}/cancel", headers=headers_user)
        print("Cancel Borrow Request:")
        print(res_cancel.status_code, res_cancel.json())
