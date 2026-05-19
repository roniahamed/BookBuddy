import requests

def test_self_suspension():
    login_url = "http://localhost:8001/api/v1/auth/login"
    login_payload = {
        "email": "admin@bookbuddy.com",
        "password": "admin123"
    }
    
    print("Logging in as Admin...")
    r = requests.post(login_url, json=login_payload)
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} - {r.text}")
        return
        
    token = r.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Verify our current user ID first by calling /auth/me
    print("Checking current admin user profile...")
    me_r = requests.get("http://localhost:8001/api/v1/auth/me", headers=headers)
    if me_r.status_code != 200:
        print(f"Failed to fetch /auth/me: {me_r.status_code} - {me_r.text}")
        return
        
    admin_id = me_r.json().get("id")
    print(f"Logged in as admin with ID: {admin_id}")
    
    # Try to suspend self
    suspend_url = f"http://localhost:8001/api/v1/admin/users/{admin_id}/suspend"
    suspend_payload = {
        "reason": "Deactivating myself for testing"
    }
    
    print(f"Attempting self-suspension at {suspend_url}...")
    susp_r = requests.patch(suspend_url, json=suspend_payload, headers=headers)
    print(f"Response status code: {susp_r.status_code}")
    print(f"Response body: {susp_r.json()}")
    
    if susp_r.status_code == 400 and "You cannot suspend your own account" in susp_r.json().get("detail", ""):
        print("\033[92mSUCCESS: Self-suspension blocked correctly with 400 Bad Request!\033[0m")
    else:
        print("\033[91mFAILURE: Self-suspension was not blocked as expected!\033[0m")

if __name__ == "__main__":
    test_self_suspension()
