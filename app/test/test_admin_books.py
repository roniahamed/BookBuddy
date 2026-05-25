import requests
import os
import psycopg2
from pprint import pprint

BASE = "http://localhost:8001/api/v1"

def test_admin_books():
    print("Running Admin Books Test...")
    
    # 1. Clear db for tests
    conn = psycopg2.connect("dbname=bookbuddy user=postgres password=admin host=localhost port=5432")
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE users CASCADE;")
    cur.execute("TRUNCATE TABLE genres CASCADE;")
    cur.execute("INSERT INTO genres (id, name) VALUES (1, 'Test Genre');")
    conn.commit()
    
    # 2. Register Admin User
    r = requests.post(f"{BASE}/auth/register", json={
        "full_name": "Admin User",
        "email": "admin@example.com",
        "password": "AdminPassword1"
    })
    assert r.status_code == 201
    
    # 3. Promote to Admin
    cur.execute("UPDATE users SET role='admin' WHERE email='admin@example.com';")
    conn.commit()
    
    # 4. Login Admin
    r = requests.post(f"{BASE}/auth/login", json={
        "email": "admin@example.com",
        "password": "AdminPassword1"
    })
    assert r.status_code == 200
    token_admin = r.json()["access_token"]
    h_admin = {"Authorization": f"Bearer {token_admin}"}
    
    # 5. Upload Book
    r = requests.post(f"{BASE}/books", headers=h_admin, data={
        "title": "Admin Book",
        "author_name": "Admin Author",
        "genre_id": 1,
        "condition": "New"
    })
    assert r.status_code == 201
    book_id = r.json()["id"]
    
    print(f"Book created: {book_id}")
    
    # 6. Admin Update Book
    r = requests.patch(f"{BASE}/admin/books/{book_id}", headers=h_admin, json={
        "availability": "unavailable",
        "description": "Hidden by admin due to policy violation"
    })
    assert r.status_code == 200, f"Expected 200, got {r.status_code} - {r.text}"
    print("Admin updated book successfully!")
    
    # 7. Admin Delete Book
    r = requests.delete(f"{BASE}/admin/books/{book_id}", headers=h_admin)
    assert r.status_code == 200, f"Expected 200, got {r.status_code} - {r.text}"
    print("Admin deleted book successfully!")
    
    # 8. Verify Book is Gone
    cur.execute(f"SELECT COUNT(*) FROM books WHERE id={book_id}")
    count = cur.fetchone()[0]
    assert count == 0, f"Expected 0 books, found {count}"
    print("Book is completely removed from DB!")
    
    print("✅ All Admin Book Tests Passed!")
    
if __name__ == "__main__":
    test_admin_books()
