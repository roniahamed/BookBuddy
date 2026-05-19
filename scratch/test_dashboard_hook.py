import asyncio
from unittest.mock import MagicMock
from starlette.requests import Request
from fastapi import HTTPException
import sys
import os

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.modules.admin.dashboard import UserAdmin
from app.modules.users.model import User

async def test_dashboard_hook():
    print("Testing SQLAdmin UserAdmin on_model_change hook...")
    
    # 1. Test case: Admin deactivating themselves (Should be blocked)
    model_self = User(email="admin@bookbuddy.com", is_active=True)
    data_deactivate = {"is_active": False}
    
    request_self = MagicMock(spec=Request)
    request_self.session = {"admin_email": "admin@bookbuddy.com"}
    
    # Call the on_model_change method directly on the class
    try:
        await UserAdmin.on_model_change(None, data_deactivate, model_self, is_created=False, request=request_self)
        print("\033[91mFAILURE: Did not raise exception on self-deactivation!\033[0m")
    except HTTPException as e:
        if e.status_code == 400 and "You cannot deactivate your own account" in e.detail:
            print("\033[92mSUCCESS: Correctly blocked admin from deactivating themselves in SQLAdmin!\033[0m")
        else:
            print(f"\033[91mFAILURE: Raised unexpected HTTPException: {e.status_code} - {e.detail}\033[0m")
    except Exception as e:
        print(f"\033[91mFAILURE: Raised unexpected error type: {type(e).__name__} - {e}\033[0m")

    # 2. Test case: Admin deactivating ANOTHER user (Should be allowed)
    model_other = User(email="jane.smith@example.com", is_active=True)
    try:
        await UserAdmin.on_model_change(None, data_deactivate, model_other, is_created=False, request=request_self)
        print("\033[92mSUCCESS: Allowed deactivating another user account.\033[0m")
    except Exception as e:
        print(f"\033[91mFAILURE: Raised exception on deactivating another user: {e}\033[0m")

    # 3. Test case: Admin saving themselves without changing is_active or keeping it True (Should be allowed)
    data_active = {"is_active": True}
    try:
        await UserAdmin.on_model_change(None, data_active, model_self, is_created=False, request=request_self)
        print("\033[92mSUCCESS: Allowed saving own admin profile when keeping it active.\033[0m")
    except Exception as e:
        print(f"\033[91mFAILURE: Raised exception on saving active profile: {e}\033[0m")

if __name__ == "__main__":
    asyncio.run(test_dashboard_hook())
