import sys
import os

from unittest.mock import MagicMock
from app.modules.books.service import BookService
from app.modules.books.schema import BookCreateRequest
from app.modules.users.model import User

def test_create_book_location_fields():
    # Mock the DB session
    mock_db = MagicMock()
    service = BookService(mock_db)
    
    # Mock the repo methods
    service.repo = MagicMock()
    service.repo.db = mock_db
    
    # Setup mock returns
    mock_author = MagicMock()
    mock_author.id = 5
    service.repo.get_or_create_author.return_value = mock_author
    
    mock_genre = MagicMock()
    mock_genre.id = 36
    service.repo.get_or_create_genre.return_value = mock_genre
    
    mock_book = MagicMock()
    mock_book.id = 9
    mock_book.title = "Labore pariatur Dol"
    service.repo.create_book.return_value = mock_book
    
    # Create the user
    user = User(id=2, full_name="Test User", role="user")
    
    # Create the request matching the user's payload
    data = BookCreateRequest(
        title="Labore pariatur Dol",
        author_id=5,
        genre_id=36,
        description="Quod eum exercitatio",
        condition="Good",
        borrow_duration_days=30,
        location="Air Nostrum Lamsa Hangar de Manteni...",
        latitude=39.4806874,
        longitude=-0.4616278,
    )
    
    # Run the service method
    # We mock get_book_detail to return just a simple dict instead of full schema to avoid DB calls
    service.get_book_detail = MagicMock(return_value={"status": "success"})
    
    # Call the method
    service.create_book(user, data)
    
    # Assert that create_book was called with the right dictionary
    call_args = service.repo.create_book.call_args
    assert call_args is not None, "repo.create_book was never called!"
    
    user_id, book_dict = call_args[0]
    
    print("Database insert payload keys:", book_dict.keys())
    print(f"Latitude passed to DB: {book_dict.get('latitude')}")
    print(f"Longitude passed to DB: {book_dict.get('longitude')}")
    print(f"Location passed to DB: {book_dict.get('location')}")
    
    if book_dict.get('latitude') == 39.4806874 and book_dict.get('longitude') == -0.4616278:
        print("\nSUCCESS: The fix is working! The location fields are being passed to the DB.")
    else:
        print("\nFAILURE: The location fields are missing!")

if __name__ == "__main__":
    test_create_book_location_fields()
