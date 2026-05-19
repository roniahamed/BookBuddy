import requests

def test_all_missing_images():
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

    # Test Part A: Fetch /api/v1/admin/users
    print("\n2. Fetching /api/v1/admin/users...")
    users_url = "http://localhost:8001/api/v1/admin/users?page=1&size=5"
    users_r = requests.get(users_url, headers=headers)
    if users_r.status_code == 200:
        items = users_r.json().get("items", [])
        if items:
            first_user = items[0]
            print(f"First user: '{first_user.get('full_name')}'")
            print(f"  avatar_url: {first_user.get('avatar_url')}")
            if "avatar_url" in first_user:
                print("\033[92mSUCCESS: avatar_url is present in the admin users list!\033[0m")
            else:
                print("\033[91mFAILURE: avatar_url is missing from the admin users list!\033[0m")
    else:
        print(f"Failed to fetch users: {users_r.status_code}")

    # Test Part B: Fetch /api/v1/admin/users/1
    print("\n3. Fetching /api/v1/admin/users/1...")
    detail_url = "http://localhost:8001/api/v1/admin/users/1"
    detail_r = requests.get(detail_url, headers=headers)
    if detail_r.status_code == 200:
        detail = detail_r.json()
        print(f"User detail: '{detail.get('full_name')}'")
        print(f"  avatar_url: {detail.get('avatar_url')}")
        if "avatar_url" in detail:
            print("\033[92mSUCCESS: avatar_url is present in the admin user detail!\033[0m")
        else:
            print("\033[91mFAILURE: avatar_url is missing from the admin user detail!\033[0m")
    else:
        print(f"Failed to fetch user detail: {detail_r.status_code}")

    # Test Part C: Fetch /api/v1/admin/books
    print("\n4. Fetching /api/v1/admin/books...")
    books_url = "http://localhost:8001/api/v1/admin/books?page=1&size=5"
    books_r = requests.get(books_url, headers=headers)
    if books_r.status_code == 200:
        items = books_r.json().get("items", [])
        if items:
            first_book = items[0]
            print(f"First book: '{first_book.get('title')}'")
            print(f"  front_cover_url: {first_book.get('front_cover_url')}")
            print(f"  owner_avatar_url: {first_book.get('owner_avatar_url')}")
            if "owner_avatar_url" in first_book:
                print("\033[92mSUCCESS: owner_avatar_url is present in the admin book list!\033[0m")
            else:
                print("\033[91mFAILURE: owner_avatar_url is missing from the admin book list!\033[0m")
    else:
        print(f"Failed to fetch books: {books_r.status_code}")

    # Test Part D: Fetch /api/v1/admin/reviews
    print("\n5. Fetching /api/v1/admin/reviews...")
    reviews_url = "http://localhost:8001/api/v1/admin/reviews?page=1&size=5"
    reviews_r = requests.get(reviews_url, headers=headers)
    if reviews_r.status_code == 200:
        items = reviews_r.json().get("items", [])
        if items:
            first_review = items[0]
            print(f"First review: by '{first_review.get('reviewer_name')}' for '{first_review.get('reviewee_name')}'")
            print(f"  reviewer_avatar_url: {first_review.get('reviewer_avatar_url')}")
            print(f"  reviewee_avatar_url: {first_review.get('reviewee_avatar_url')}")
            if "reviewer_avatar_url" in first_review and "reviewee_avatar_url" in first_review:
                print("\033[92mSUCCESS: Both reviewer and reviewee avatar URLs are present in the admin reviews list!\033[0m")
            else:
                print("\033[91mFAILURE: Avatar URLs are missing from the admin reviews list!\033[0m")
    else:
        print(f"Failed to fetch reviews: {reviews_r.status_code}")

if __name__ == "__main__":
    test_all_missing_images()
