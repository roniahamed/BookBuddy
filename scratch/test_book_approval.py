import asyncio
from app.core.database import SessionLocal
from app.modules.users.model import User
from app.modules.books.model import Book
from app.modules.books.service import BookService
from app.modules.admin.service import AdminManagementService
from app.modules.books.schema import BookCreateRequest

async def main():
    db = SessionLocal()
    
    try:
        print("Testing book approval workflow...")
        
        # 1. Create a dummy user
        user = db.query(User).filter(User.email == "test_approvals@example.com").first()
        if not user:
            user = User(email="test_approvals@example.com", full_name="Test User", password_hash="pw", is_active=True, role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            print("No admin user found. Creating one...")
            admin = User(email="admin_approvals@example.com", full_name="Admin User", password_hash="pw", is_active=True, role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            
        # 2. Upload a book as a normal user
        book_svc = BookService(db)
        import uuid
        unique_title = f"Test Book {uuid.uuid4()}"
        data = BookCreateRequest(
            title=unique_title,
            author_name="John Doe",
            condition="Good",
            borrow_duration_days=14,
            language="English"
        )
        new_book_response = book_svc.create_book(user, data)
        book_id = new_book_response.id
        print(f"Book created with ID: {book_id}")
        
        # Verify it's pending
        book_in_db = db.query(Book).filter(Book.id == book_id).first()
        assert book_in_db.approval_status == "pending", "Book should be pending!"
        print("Book is pending.")
        
        # Verify it doesn't show in public list
        from app.modules.books.repository import BookRepository
        from app.modules.books.filters import BookFilters
        repo = BookRepository(db)
        public_books, total = repo.get_books_filtered(BookFilters(search=unique_title, radius_km=None, user_lat=None, user_lon=None, genre_id=None, condition=None, availability=None))
        assert total == 0, "Book should not be visible in public listings!"
        print("Book is hidden from public listings.")
        
        # 3. Admin sees the book in admin dashboard
        admin_svc = AdminManagementService(db)
        admin_books_response = admin_svc.list_books(approval_status="pending")
        assert admin_books_response.pending_approvals >= 1, "Pending approvals metric should be >= 1"
        print(f"Admin sees {admin_books_response.pending_approvals} pending approvals in metrics.")
        
        # 4. Admin approves the book
        admin_svc.approve_book(book_id, admin)
        
        # Verify it's approved
        book_in_db = db.query(Book).filter(Book.id == book_id).first()
        assert book_in_db.approval_status == "approved", "Book should be approved!"
        print("Book is now approved.")
        
        # Verify it shows in public list
        public_books, total = repo.get_books_filtered(BookFilters(search=unique_title, radius_km=None, user_lat=None, user_lon=None, genre_id=None, condition=None, availability=None))
        assert total >= 1, "Book should be visible in public listings now!"
        print("Book is visible in public listings.")
        
        print("Test passed successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
