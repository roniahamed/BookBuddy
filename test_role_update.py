import sys
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.modules.auth.dependencies import get_current_user
from app.core.dependencies import get_db
from app.modules.users.model import User

client = TestClient(app)

def test_update_user_role():
    # 1. Create a mock admin user
    mock_admin = User(id=1, full_name="Admin", email="admin@test.com", role="admin", is_active=True)
    
    # Override the auth dependency
    app.dependency_overrides[get_current_user] = lambda: mock_admin

    # 2. Mock the DB session and repository
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    
    # We will patch the service to return our mocked response
    # Or, we can just patch the repository methods
    # Wait, instead of patching the whole service, let's just patch the repository via unittest.mock
    from app.modules.admin.repository import AdminManagementRepository
    
    # Mocking get_user_by_id
    mock_target_user = User(id=2, full_name="Target", email="target@test.com", role="user", is_active=True)
    
    original_get_user_by_id = AdminManagementRepository.get_user_by_id
    AdminManagementRepository.get_user_by_id = MagicMock(return_value=mock_target_user)
    
    original_update_user_role = AdminManagementRepository.update_user_role
    AdminManagementRepository.update_user_role = MagicMock(return_value=mock_target_user)
    
    # Also need to mock log_platform_activity since it inserts into DB
    import app.modules.admin.service as admin_service
    original_log = admin_service.log_platform_activity
    admin_service.log_platform_activity = MagicMock()

    try:
        # 3. Make the request
        payload = {"role": "admin"}
        response = client.patch("/api/v1/admin/users/2/role", json=payload)
        
        print("Response status code:", response.status_code)
        print("Response JSON:", response.json())
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.json()}"
        assert response.json()["message"] == "User 'target@test.com' role updated to 'admin'."
        
        AdminManagementRepository.update_user_role.assert_called_once_with(2, "admin")
        print("\nSUCCESS: The endpoint works perfectly!")

    finally:
        # Restore overrides
        app.dependency_overrides.clear()
        AdminManagementRepository.get_user_by_id = original_get_user_by_id
        AdminManagementRepository.update_user_role = original_update_user_role
        admin_service.log_platform_activity = original_log

if __name__ == "__main__":
    test_update_user_role()
