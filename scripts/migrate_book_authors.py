import sys
import os

# Add the parent directory to sys.path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
from app.modules.books.model import Book, Author, Review
from app.modules.users.model import User
from app.modules.borrowing.model import BorrowRequest

def migrate_authors():
    db: Session = SessionLocal()
    try:
        # Get books and their author_name using raw SQL
        result = db.execute(text("SELECT id, author_name FROM books WHERE author_name IS NOT NULL AND author_id IS NULL"))
        books = result.fetchall()
        
        author_map = {} # name -> author.id
        
        # Load existing authors
        existing_authors = db.query(Author).all()
        for a in existing_authors:
            author_map[a.name] = a.id

        updates_count = 0
        for book in books:
            book_id, author_name = book
            author_name = author_name.strip()
            
            if author_name not in author_map:
                new_author = Author(name=author_name)
                db.add(new_author)
                db.flush() # get id
                author_map[author_name] = new_author.id
            
            db.execute(
                text("UPDATE books SET author_id = :author_id WHERE id = :book_id"),
                {"author_id": author_map[author_name], "book_id": book_id}
            )
            updates_count += 1
        
        db.commit()
        print(f"Migration completed successfully. Updated {updates_count} books.")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_authors()
