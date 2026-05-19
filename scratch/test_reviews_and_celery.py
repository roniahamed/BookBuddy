import requests

def test_reviews_and_celery():
    print("1. Logging in as Admin...")
    login_url = "http://localhost:8001/api/v1/auth/login"
    login_payload = {
        "email": "admin@bookbuddy.com",
        "password": "admin123"
    }
    r = requests.post(login_url, json=login_payload)
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} - {r.text}")
        return
        
    token = r.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Test Part A: Fetch /api/v1/admin/reviews
    print("\n2. Fetching /api/v1/admin/reviews...")
    reviews_url = "http://localhost:8001/api/v1/admin/reviews?page=1&size=20"
    reviews_r = requests.get(reviews_url, headers=headers)
    if reviews_r.status_code != 200:
        print(f"Failed to fetch admin reviews: {reviews_r.status_code} - {reviews_r.text}")
        return
        
    items = reviews_r.json().get("items", [])
    if not items:
        print("Warning: No reviews found in the database.")
    else:
        first_review = items[0]
        print(f"First review by '{first_review.get('reviewer_name')}' for book '{first_review.get('book_title')}'")
        print(f"  reviewer_avatar_url: {first_review.get('reviewer_avatar_url')}")
        if "reviewer_avatar_url" in first_review:
            print("\033[92mSUCCESS: reviewer_avatar_url is present in the admin reviews API list!\033[0m")
        else:
            print("\033[91mFAILURE: reviewer_avatar_url is missing from the admin reviews response!\033[0m")

    # Test Part B: Trigger single user push notification broadcast
    print("\n3. Dispatched a test broadcast to single user (ID=1) to verify celery worker...")
    broadcast_url = "http://localhost:8001/api/v1/admin/notifications/broadcast"
    payload = {
        "title": "Celery Health Check",
        "body": "Your push notification background task completed successfully!",
        "target": "user",
        "user_id": 1,
        "send_push": True,
        "send_email": False
    }
    broadcast_r = requests.post(broadcast_url, json=payload, headers=headers)
    print(f"Broadcast API response: {broadcast_r.status_code} - {broadcast_r.text}")
    
    if broadcast_r.status_code == 200:
        print("\033[92mSUCCESS: Broadcast API request accepted. Check celery console for clean execution without type crashes!\033[0m")
    else:
        print("\033[91mFAILURE: Broadcast API returned non-200 status!\033[0m")

if __name__ == "__main__":
    test_reviews_and_celery()
