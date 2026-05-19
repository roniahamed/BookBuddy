import requests
import os

def test_admin_covers_and_upload():
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

    # Test Part A: Fetch /api/v1/admin/books
    print("\n2. Fetching /api/v1/admin/books...")
    books_url = "http://localhost:8001/api/v1/admin/books?page=1&size=20"
    books_r = requests.get(books_url, headers=headers)
    if books_r.status_code != 200:
        print(f"Failed to fetch admin books: {books_r.status_code} - {books_r.text}")
        return
        
    items = books_r.json().get("items", [])
    if not items:
        print("Warning: No books found in the database.")
    else:
        first_book = items[0]
        print(f"First book: '{first_book.get('title')}' by {first_book.get('author_name')}")
        print(f"  front_cover_url: {first_book.get('front_cover_url')}")
        print(f"  back_cover_url: {first_book.get('back_cover_url')}")
        if "front_cover_url" in first_book and "back_cover_url" in first_book:
            print("\033[92mSUCCESS: Cover fields are present in the admin books API list!\033[0m")
        else:
            print("\033[91mFAILURE: Cover fields are missing from the admin books list response!\033[0m")

    # Test Part B: Direct image upload to /api/v1/books/upload-image
    print("\n3. Testing direct image upload to /api/v1/books/upload-image...")
    
    # Create a small dummy file to upload
    dummy_filename = "dummy_cover.png"
    with open(dummy_filename, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        
    upload_url = "http://localhost:8001/api/v1/books/upload-image"
    try:
        with open(dummy_filename, "rb") as df:
            files = {"file": (dummy_filename, df, "image/png")}
            upload_r = requests.post(upload_url, files=files, headers=headers)
            
        print(f"Upload response status: {upload_r.status_code}")
        print(f"Upload response body: {upload_r.json()}")
        
        if upload_r.status_code == 200 and "url" in upload_r.json():
            uploaded_url = upload_r.json()["url"]
            print(f"\033[92mSUCCESS: Image uploaded successfully! URL: {uploaded_url}\033[0m")
            
            # Verify the uploaded image is accessible
            print("\n4. Accessing the uploaded image URL...")
            get_img_r = requests.get(uploaded_url)
            print(f"Static file fetch status: {get_img_r.status_code}")
            if get_img_r.status_code == 200:
                print("\033[92mSUCCESS: Uploaded image is fully accessible and served by FastAPI static mount!\033[0m")
            else:
                print("\033[91mFAILURE: Uploaded image URL returned non-200 status!\033[0m")
        else:
            print("\033[91mFAILURE: Upload endpoint returned incorrect response!\033[0m")
            
    finally:
        # Clean up the local dummy file
        if os.path.exists(dummy_filename):
            os.remove(dummy_filename)

if __name__ == "__main__":
    test_admin_covers_and_upload()
