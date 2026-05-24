# Admin APIs Documentation

The Admin APIs are used for platform configuration, user and book management, platform statistics, reviews monitoring, contact messages, and broadcasting notifications. **All endpoints require an admin role JWT token.**

**Base URL:** `/api/v1/admin`

---

## 1. Config Management

### 1.1 List All Configurations
**`GET /config`**
Get all admin-configurable settings (borrow points, OTP expiry, nearby radius, etc.).

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "key": "borrow_reward_borrower_points",
      "value": "5",
      "description": "Points rewarded to borrower",
      "updated_at": "2026-05-24T00:00:00Z"
    }
  ]
}
```

### 1.2 Get Single Configuration
**`GET /config/{key}`**
Get a single configuration value by its key.

**Response:**
```json
{
  "id": 1,
  "key": "borrow_reward_borrower_points",
  "value": "5",
  "description": "Points rewarded to borrower",
  "updated_at": "2026-05-24T00:00:00Z"
}
```

### 1.3 Update Configuration
**`PATCH /config/{key}`**
Update a configuration value.

**Payload (JSON):**
```json
{
  "value": "15"
}
```

**Response:** Updated configuration object.

---

## 2. Platform Stats

### 2.1 Get Platform Stats
**`GET /stats`**
Get a real-time snapshot of the platform for the admin dashboard home screen.

**Response:**
```json
{
  "total_users": 100,
  "active_users": 95,
  "suspended_users": 5,
  "total_books": 500,
  "available_books": 300,
  "borrowed_books": 200,
  "total_borrow_requests": 150,
  "pending_borrow_requests": 20,
  "active_borrow_requests": 100,
  "overdue_borrow_requests": 5,
  "pending_book_approvals": 15,
  "total_reviews": 350,
  "avg_platform_rating": 4.5,
  "recent_borrows": [
    {
      "id": 1,
      "requester_name": "Jane Doe",
      "requester_avatar_url": "http://...",
      "book_title": "1984",
      "status": "pending",
      "requested_date": "2026-05-24T00:00:00Z"
    }
  ],
  "recent_activities": [
    {
      "id": 1,
      "user_name": "John Doe",
      "user_avatar_url": "http://...",
      "action_type": "book_added",
      "description": "John shared a new book: 'Dune'",
      "created_at": "2026-05-24T00:00:00Z"
    }
  ]
}
```

---

## 3. User Management

### 3.1 List All Users
**`GET /users`**
Paginated list of all registered users with metrics.

**Query Parameters:**
- `search` (string, optional): Search by name or email
- `role` (string, optional): 'user' or 'admin'
- `is_active` (boolean, optional): Active status
- `page` (int, default: 1): Page number
- `size` (int, default: 20): Items per page

**Response:**
```json
{
  "metrics": {
    "total_members": 100,
    "total_borrow_requests": 150,
    "avg_rating": 4.5
  },
  "items": [
    {
      "id": 1,
      "full_name": "John Doe",
      "email": "john@example.com",
      "avatar_url": "http://...",
      "role": "user",
      "is_active": true,
      "credits": 50,
      "avg_rating": 4.8,
      "books_uploaded": 5,
      "borrow_count": 3,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5,
  "has_next": true,
  "has_prev": false
}
```

### 3.2 Get User Detail
**`GET /users/{user_id}`**
Full user detail for admin view, including computed stats.

**Response:**
```json
{
  "id": 1,
  "full_name": "John Doe",
  "email": "john@example.com",
  "role": "user",
  "is_active": true,
  "credits": 50,
  "avg_rating": 4.8,
  "books_uploaded": 5,
  "books_available": 3,
  "books_borrowed": 2,
  "reviews_written": 4,
  "reviews_received": 3,
  "created_at": "2026-01-01T00:00:00Z"
}
```

### 3.3 Suspend User
**`PATCH /users/{user_id}/suspend`**
Deactivate a user account. Cannot suspend another admin.

**Payload (JSON):**
```json
{
  "reason": "Repeatedly failed to return books on time."
}
```

### 3.4 Reactivate User
**`PATCH /users/{user_id}/activate`**
Restore a previously suspended user account.

### 3.5 Delete User
**`DELETE /users/{user_id}`**
Permanently delete a user account and all cascading data.

---

## 4. Book Management

### 4.1 List Books
**`GET /books`**
Paginated list of all books on the platform.

**Query Parameters:**
- `search` (string, optional): Title or author
- `availability` (string, optional): available | borrowed | unavailable
- `genre_id` (int, optional)
- `approval_status` (string, optional): pending | approved | rejected
- `page` (int, default: 1)
- `size` (int, default: 20)

### 4.2 Update Book Status / Description
**`PATCH /books/{book_id}`**
Admin override to update a book's availability status or description.

**Payload (JSON):**
```json
{
  "availability": "unavailable",
  "description": "Removed: Policy violation."
}
```

### 4.3 Approve Book
**`PATCH /books/{book_id}/approve`**
Approve a pending book.

### 4.4 Reject Book
**`PATCH /books/{book_id}/reject`**
Reject a pending book.

### 4.5 Delete Book
**`DELETE /books/{book_id}`**
Permanently delete a book listing and related data.

---

## 5. Reviews & Ratings Monitoring

### 5.1 List Reviews
**`GET /reviews`**
Paginated list of all community reviews.

**Query Parameters:**
- `book_id` (int, optional)
- `min_rating` (float, optional)
- `max_rating` (float, optional)
- `page` (int, default: 1)
- `size` (int, default: 20)

### 5.2 Delete Review
**`DELETE /reviews/{review_id}`**
Permanently remove an abusive or fraudulent review. Automatically recalculates affected ratings.

---

## 6. Notifications Broadcast

### 6.1 Broadcast Notification
**`POST /notifications/broadcast`**
Send a push notification (FCM) and/or email to all active users or a specific user.

**Payload (JSON):**
```json
{
  "title": "Platform Maintenance",
  "body": "BookBuddy will be down for maintenance on Sunday from 2–4 AM UTC.",
  "target": "all",
  "user_id": null,
  "send_email": true,
  "send_push": true
}
```

---

## 7. Contact Messages

### 7.1 List Contact Messages
**`GET /contacts`**
List all contact form messages sent by users.

**Query Parameters:**
- `page` (int, default: 1)
- `size` (int, default: 20)

### 7.2 Get Single Contact Message
**`GET /contacts/{message_id}`**
Get details of a specific contact message.

---

## 8. Platform Activity & Borrows

### 8.1 List Borrow Requests
**`GET /borrows`**
List all borrow requests across the platform.

**Query Parameters:**
- `status` (string, optional): pending, active, returned, etc.
- `page` (int, default: 1)
- `size` (int, default: 20)

### 8.2 List Activities
**`GET /activities`**
List all system activities (e.g., books added, reviews posted).

**Query Parameters:**
- `page` (int, default: 1)
- `size` (int, default: 20)
