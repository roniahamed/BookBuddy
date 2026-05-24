# BookBuddy API Documentation - Books Module

This document outlines the REST APIs for the BookBuddy platform, covering the books, genres, authors, and reviews modules. It is designed for frontend developers integrating these endpoints.

> [!NOTE]
> All endpoints requiring authentication expect a standard `Authorization: Bearer <token>` header.

---

## 1. Books API
**Base Path:** `/books`

### 1.1 Browse Books
**`GET /books`**
Browse and search books with powerful filtering options.

**Query Parameters:**
- `page` (int, default: 1): Page number.
- `per_page` (int, default: 20): Items per page.
- `search` (str, optional): Text search for title, author, genre.
- `genre_id` (int, optional): Filter by genre ID.
- `condition` (str, optional): Filter by condition (New, Good, Used).
- `availability` (str, optional): Filter by availability status.
- `sort_by` (str, optional): Sort order (e.g., distance).
- `lat` (float, optional): User latitude for proximity sorting.
- `lng` (float, optional): User longitude for proximity sorting.

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "title": "A Tale of Love and Darkness",
      "author": { "id": 1, "name": "Amos Oz" },
      "front_cover_image": "http://...",
      "back_cover_image": "http://...",
      "condition": "Good",
      "availability": "available",
      "avg_rating": 4.5,
      "location": "Westheimer Rd. Santa Ana, Illinois",
      "latitude": 33.7455,
      "longitude": -117.8677,
      "borrow_duration_days": 30,
      "distance_km": 5.2,
      "genre": { "id": 1, "name": "Biography" },
      "owner": {
        "id": 2,
        "full_name": "John Doe",
        "avatar_url": "http://...",
        "location": "Illinois",
        "avg_rating": 4.8
      },
      "is_wishlisted": false,
      "created_at": "2026-05-24T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

### 1.2 Books Near You
**`GET /books/nearby`**
Get available books near the authenticated user's location, sorted by distance.
*(Requires Authentication)*

**Query Parameters:**
- `radius_km` (float, default: 50, range 1-500)
- `page` (int, default: 1)
- `per_page` (int, default: 20)

**Response:** Paginated Book list (Same structure as 1.1)

### 1.3 Recommended Books
**`GET /books/recommended`**
Personalized recommendations based on borrowing history.
*(Requires Authentication)*

**Query Parameters:** `page`, `per_page`

**Response:** Paginated Book list (Same structure as 1.1)

### 1.4 New Arrivals
**`GET /books/new-arrivals`**
Most recently added available books.

**Query Parameters:** `page`, `per_page`

**Response:** Paginated Book list (Same structure as 1.1)

### 1.5 Top Rated
**`GET /books/top-rated`**
Highest-rated available books based on community ratings.

**Query Parameters:** `page`, `per_page`

**Response:** Paginated Book list (Same structure as 1.1)

### 1.6 My Uploaded Books
**`GET /books/my-books`**
All books uploaded by the current user.
*(Requires Authentication)*

**Query Parameters:** `page`, `per_page`

**Response:** Paginated Book list (Same structure as 1.1)

### 1.7 My Wishlist
**`GET /books/wishlist`**
Get all books in the current user's wishlist.
*(Requires Authentication)*

**Query Parameters:** `page`, `per_page`

**Response:** Paginated Book list (Same structure as 1.1, wrapped in wishlist item)

### 1.8 Book Details
**`GET /books/{book_id}`**
Full details for a single book.

**Path Parameters:**
- `book_id` (int, required)

**Response:**
```json
{
  "id": 1,
  "title": "A Tale of Love and Darkness",
  "author": { "id": 1, "name": "Amos Oz" },
  "description": "A deeply personal memoir exploring family...",
  "front_cover_image": "http://...",
  "back_cover_image": "http://...",
  "condition": "Good",
  "availability": "available",
  "avg_rating": 4.5,
  "borrow_duration_days": 30,
  "location": "Westheimer Rd. Santa Ana, Illinois",
  "latitude": 33.7455,
  "longitude": -117.8677,
  "distance_km": 5.2,
  "genre": { "id": 1, "name": "Biography" },
  "owner": {
    "id": 2,
    "full_name": "John Doe",
    "avatar_url": "http://...",
    "location": "Illinois",
    "avg_rating": 4.8
  },
  "is_wishlisted": false,
  "reviews_count": 10,
  "created_at": "2026-05-24T00:00:00Z"
}
```

### 1.9 Upload Book
**`POST /books`**
List a new book for community sharing.
*(Requires Authentication)*

**Payload (Multipart Form Data):**
- `title` (string, required): Book title
- `author_id` (int, optional): Author ID from `/authors`
- `author_name` (string, optional): Author name if creating a new one
- `genre_id` (int, optional): Genre ID from `/genres`
- `genre_name` (string, optional): Genre name if creating a new one
- `description` (string, optional): Book description
- `language` (string, default: "English"): Book language
- `condition` (string, default: "Good"): "New", "Good", or "Used"
- `borrow_duration_days` (int, default: 30): Max borrow days
- `location` (string, optional): Pickup address
- `latitude` (float, optional)
- `longitude` (float, optional)
- `front_cover_image` (file, optional): File upload
- `back_cover_image` (file, optional): File upload

**Response:** Same object as `Book Details` (1.8) (HTTP 201 Created)

### 1.10 Update Book Details
**`PATCH /books/{book_id}`**
Update book information (Owner only).
*(Requires Authentication)*

**Payload (JSON):**
```json
{
  "title": "New Title",
  "author_id": 1,
  "genre_id": 2,
  "description": "Updated description",
  "front_cover_image": "http://...",
  "back_cover_image": "http://...",
  "condition": "Used",
  "borrow_duration_days": 15,
  "location": "New Address",
  "latitude": 33.7455,
  "longitude": -117.8677,
  "availability": "unavailable"
}
```

**Response:** Same object as `Book Details` (1.8)

### 1.11 Delete Book
**`DELETE /books/{book_id}`**
Permanently delete a book listing (Owner only).
*(Requires Authentication)*

**Response:** HTTP 200/204 Success

### 1.12 Direct Image Upload
**`POST /books/upload-image`**
Upload an image file directly (front or back cover) to get a public static URL.
*(Requires Authentication)*

**Payload (Multipart Form Data):**
- `file` (file, required)

**Response:**
```json
{
  "url": "http://yourdomain.com/static/uploads/uuid.jpg"
}
```

### 1.13 Add/Remove from Wishlist
**`POST /books/{book_id}/wishlist`** - Add book to wishlist.
**`DELETE /books/{book_id}/wishlist`** - Remove book from wishlist.
*(Requires Authentication)*

**Response:** Success status code.

### 1.14 Translate Book Details
**`GET /books/{book_id}/translate`**
Auto-translate book details (title, description, author) to the target language.

**Query Parameters:**
- `lang` (string, default: "HE"): Target language code (EN or HE)

**Response:**
```json
{
  "book_id": 1,
  "original_title": "A Tale of Love and Darkness",
  "title": "סיפור על אהבה וחושך",
  "description": "זיכרונות אישיים עמוקים החוקרים את המשפחה...",
  "author_name": "עמוס עוז"
}
```


---

## 2. Genres API
**Base Path:** `/genres`

### 2.1 List Genres
**`GET /genres`**
Get all available book genres/categories.

**Query Parameters:**
- `search` (str, optional): Search by genre name
- `sort_by` (str, default: "name_asc"): Sort ("name_asc" or "name_desc")
- `page`, `per_page` (int)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Biography"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 100,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

### 2.2 Create Genre
**`POST /genres`**
*(Requires Authentication)*

**Payload (JSON):**
```json
{
  "name": "Science Fiction"
}
```

**Response:** Created Genre object (Same structure as 2.1 items)


---

## 3. Authors API
**Base Path:** `/authors`

### 3.1 List Authors
**`GET /authors`**
Get all authors.

**Query Parameters:**
- `search` (str, optional): Search by author name
- `sort_by` (str, default: "name_asc"): Sort ("name_asc" or "name_desc")
- `page`, `per_page` (int)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Amos Oz"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 100,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

### 3.2 Create Author
**`POST /authors`**
*(Requires Authentication)*

**Payload (JSON):**
```json
{
  "name": "J.K. Rowling"
}
```

**Response:** Created Author object (Same structure as 3.1 items)


---

## 4. Reviews API

### 4.1 Get Book Reviews
**`GET /books/{book_id}/reviews`**
Get community ratings/reviews for a specific book.

**Query Parameters:** `page`, `per_page`

**Response:** Paginated Review list (Same structure as 4.2 items)

### 4.2 List All Reviews
**`GET /reviews`**
Get all community reviews across all users and books.

**Query Parameters:**
- `book_id` (int, optional): Filter by book ID
- `user_id` (int, optional): Filter by user ID
- `page`, `per_page` (int)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "rating": 4.8,
      "review_text": "I recently borrowed a book from this platform, and it was an amazing experience.",
      "created_at": "2026-05-24T00:00:00Z",
      "reviewer": {
        "id": 5,
        "full_name": "Jane Smith",
        "avatar_url": "http://...",
        "location": "New York",
        "avg_rating": 5.0
      },
      "book_title": "A Tale of Love and Darkness",
      "book_id": 1
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

### 4.3 Submit a Review
**`POST /reviews`**
Submit a community rating for a completed borrow transaction.
*(Requires Authentication)*

**Payload (JSON):**
```json
{
  "borrow_request_id": 1,
  "rating": 4.8,
  "review_text": "I recently borrowed a book from this platform, and it was an amazing experience."
}
```

**Response:** Created Review object (Same structure as 4.2 items)

---

## 5. Borrowing API
**Base Path:** `/borrow-requests`

### 5.1 Request to Borrow a Book
**`POST /borrow-requests`**
Submit a request to borrow a book (REQUEST BOOK button). The book must be available and you cannot borrow your own books. Duplicate pending requests are not allowed.
*(Requires Authentication)*

**Payload (JSON):**
```json
{
  "book_id": 1
}
```

**Response:** HTTP 201 Created
```json
{
  "id": 1,
  "status": "pending",
  "message": "Borrow request submitted successfully"
}
```

### 5.2 My Borrowed Books
**`GET /borrow-requests/borrowed`**
Get all books you have borrowed (Borrowed tab on Profile screen). Shows countdown timer 'Return in X days Y Hours' for active borrows. Includes 'Mark as Returned' action for active loans.
*(Requires Authentication)*

**Query Parameters:** `page`, `per_page`

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "status": "active",
      "requested_at": "2026-05-24T00:00:00Z",
      "borrowed_at": "2026-05-24T00:00:00Z",
      "due_date": "2026-06-23T00:00:00Z",
      "time_remaining": "30 days 0 Hours",
      "book": {
        "id": 1,
        "title": "A Tale of Love and Darkness",
        "author_name": "Amos Oz",
        "front_cover_image": "http://...",
        "avg_rating": 4.5
      },
      "borrower": {
        "id": 3,
        "full_name": "Alice Smith",
        "avatar_url": "http://..."
      }
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

### 5.3 My Lent Out Books
**`GET /borrow-requests/lent-out`**
Get all books you have lent out to others (Lent Out tab on Profile screen). Shows 'Expected back in X days Y Hours' countdown for active loans. Includes 'Confirm Received' action for returned books.
*(Requires Authentication)*

**Query Parameters:** `page`, `per_page`

**Response:** Paginated list (Same structure as 5.2 items)

### 5.4 Borrow Request Details
**`GET /borrow-requests/{request_id}`**
Get details of a specific borrow request. Only accessible by the borrower or book owner.
*(Requires Authentication)*

**Path Parameters:**
- `request_id` (int, required)

**Response:** Single borrow request object (Same structure as 5.2 items)

### 5.5 Approve Borrow Request
**`PATCH /borrow-requests/{request_id}/approve`**
Book owner approves a pending borrow request. Automatically starts the loan: sets status to 'active', records borrowed_at timestamp, and calculates due_date. The book's availability changes to 'borrowed'.
*(Requires Authentication)*

**Response:**
```json
{
  "id": 1,
  "status": "active",
  "message": "Borrow request approved successfully"
}
```

### 5.6 Reject Borrow Request
**`PATCH /borrow-requests/{request_id}/reject`**
Book owner rejects a pending borrow request. Status changes to 'cancelled'.
*(Requires Authentication)*

**Response:** Status Update object (Same structure as 5.5)

### 5.7 Mark Book as Returned
**`PATCH /borrow-requests/{request_id}/return`**
Borrower marks a book as returned (Mark as Returned button on Borrowed tab). Status changes from 'active' to 'returned'. Owner still needs to confirm receipt.
*(Requires Authentication)*

**Response:** Status Update object (Same structure as 5.5)

### 5.8 Confirm Book Received Back
**`PATCH /borrow-requests/{request_id}/confirm`**
Book owner confirms the returned book has been received (Confirm Received button on Lent Out tab). Status changes to 'confirmed'. Book becomes 'available' again. Credits are awarded: +5 to borrower, +10 to lender.
*(Requires Authentication)*

**Response:** Status Update object (Same structure as 5.5)

### 5.9 Cancel Borrow Request
**`POST /borrow-requests/{request_id}/cancel`**
Borrower cancels a pending borrow request. Status changes to 'cancelled'.
*(Requires Authentication)*

**Response:** Status Update object (Same structure as 5.5)
