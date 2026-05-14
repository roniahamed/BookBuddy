# BookBuddy — ERD Analysis & DBDiagram Code

---

## 🔍 Observations From the UI Screens

| Screen | Data Observed |
|---|---|
| **Home** | Books with title, author, rating, condition (Good/Used/New), distance, location, availability status, genre/category filter |
| **Browse Book** | Search by title/author/genre; filters: Nearby, Available, Top Rated, New Arrivals; genres: Science, History, Self-Help, Fiction, Children's, Business, Drama, Fantasy |
| **Book Details** | Book title, author name, front/back cover images, rating, condition badge, distance, availability, borrow duration (30 day), location address, genre, description; owner's name + address + rating shown |
| **Book Details – With Review** | Community Ratings section: reviewer name, address, date, star rating (numeric + visual), review text |
| **Upload Book** | Front Cover (image), Back Cover (image), Book Title, Author Name, Genre, Borrow Duration (dropdown: 30 Days), Book Condition (New / Good / Used), Location address, Description |
| **Profile (My Book tab)** | User avatar, name, email, location, credits (coin icon = 120), average rating (⭐ 4.6); tabs: My Book / Borrowed / Lent Out / Wishlist |
| **Profile (Borrowed tab)** | List of borrowed books with countdown timer "Return in 5 days 12 Hours", "Mark as Returned" action |
| **Profile (Lent Out tab)** | List of lent-out books with "Expected back in 5 days 12 Hours", "Confirm Received" action |
| **Profile (Wishlist tab)** | Saved/favorited books |
| **Other People Profile** | Public profile: name, email, location, rating, stats: Books Uploaded / Available / Borrowed; tabs: All Books / Lent Out / Community Ratings |
| **Community Ratings** | Ratings left by others about a user's lending experience (date, star rating, review text) |
| **Chat / Messages** | Conversation list per user (All / Unread / Archive); individual messages with timestamps; context: negotiating book pickup |
| **Settings** | Preferences: Language (EN/HE toggle), Email Notification (on/off), New Message Alert (on/off) |
| **Security** | Change password; Delete Account |
| **Sign In / Log In** | Email + Password |
| **Forgot Password / Verify Code / Set New Password** | Password reset flow |
| **Onboarding** | 4 steps — app intro/location permission |
| **Permission Location** | GPS location permission request |
| **Contact** | Static support form (Name, Email, Subject, Message) — not a core data entity |

---

## 📐 Database Structure Summary

**BookBuddy** is a **community book-sharing platform** with 9 core entities:

1. **users** — Platform members. They upload books, borrow books, leave reviews, and chat. Store auth credentials, profile info, geolocation, credits, and notification preferences.
2. **books** — Physical books listed for sharing. Owned by a user. Contains metadata (title, author name, genre, condition, borrow duration, location) and cover images.
3. **genres** — Lookup table for book genres (Fiction, Science, History, etc.)
4. **borrow_requests** — Tracks a borrowing transaction from request → active loan → returned. Links borrower → book.
5. **reviews** — Community ratings left by borrowers about a lender or a book loan. Contains star rating + text.
6. **wishlist** — A user's saved/favorited books (many-to-many between users and books).
7. **messages** — Chat messages between two users, tied to a conversation thread.
8. **conversations** — A thread between two users, often triggered by a book request.
9. **user_settings** — Stores per-user notification and language preferences (1-to-1 with users).

### Key Relationships
- A **user** owns many **books** (one-to-many)
- A **book** belongs to one **genre** (many-to-one)
- A **user** can make many **borrow_requests** (one-to-many)
- A **borrow_request** links one **borrower** (user) to one **book**
- A **review** is written by one **user** about one **borrow_request**
- A **user** can wishlist many **books** (many-to-many via `wishlist`)
- A **conversation** is between exactly two **users**
- A **conversation** may reference a **book** (context for the chat)
- A **message** belongs to one **conversation**, sent by one **user**
- **user_settings** is one-to-one with **users**

---

## 🗃️ DBDiagram.io Code

Paste the code block below directly into **[dbdiagram.io](https://dbdiagram.io)**.

```
// =============================================
// BookBuddy — Community Book Sharing Platform
// ERD generated from UI/UX mockup screens
// =============================================

Table users {
  id            int         [pk, increment, note: "Primary key"]
  full_name     varchar(150) [not null, note: "Display name shown on profile and book cards"]
  email         varchar(255) [unique, not null, note: "Used for login and notifications"]
  password_hash varchar(255) [not null, note: "Hashed password (bcrypt / argon2)"]
  avatar_url    varchar(500) [null, note: "Profile photo URL"]
  location      varchar(255) [null, note: "Street address, e.g. Westheimer Rd. Santa Ana, Illinois"]
  latitude      decimal(10,7) [null, note: "GPS latitude for 'Books Near You' feature"]
  longitude     decimal(10,7) [null, note: "GPS longitude for 'Books Near You' feature"]
  credits       int         [default: 0, note: "Community coins shown on profile (coin icon)"]
  avg_rating    decimal(3,2) [default: 0.00, note: "Computed average rating from reviews received"]
  is_active     boolean     [default: true, note: "Soft-delete / account status"]
  created_at    timestamp   [default: `now()`]
  updated_at    timestamp   [default: `now()`]

  Note: "Platform members. Can own books, borrow books, review lenders, and chat."
}

Table user_settings {
  id                    int      [pk, increment]
  user_id               int      [unique, not null, ref: > users.id, note: "One-to-one with users"]
  language              varchar(10) [default: 'EN', note: "Preferred UI language, e.g. EN or HE"]
  email_notifications   boolean  [default: true, note: "Toggle for email notification alerts"]
  new_message_alert     boolean  [default: true, note: "Toggle for in-app new message alert"]
  updated_at            timestamp [default: `now()`]

  Note: "Per-user notification and language preferences (Settings screen)."
}

Table genres {
  id    int          [pk, increment]
  name  varchar(100) [unique, not null, note: "e.g. Fiction, Science, History, Fantasy, etc."]

  Note: "Lookup table for book genres. Used for filtering on Browse screen."
}

Table books {
  id                int           [pk, increment]
  owner_id          int           [not null, ref: > users.id, note: "User who uploaded/owns the book"]
  genre_id          int           [null, ref: > genres.id, note: "FK to genres lookup table"]
  title             varchar(255)  [not null, note: "Book title"]
  author_name       varchar(255)  [not null, note: "Author name (free text as entered on Upload screen)"]
  description       text          [null, note: "Description of the book and its condition"]
  front_cover_url   varchar(500)  [null, note: "URL to front cover image uploaded by owner"]
  back_cover_url    varchar(500)  [null, note: "URL to back cover image uploaded by owner"]
  condition         varchar(20)   [not null, note: "Enum: New | Good | Used"]
  borrow_duration_days int        [default: 30, note: "Max days allowed to borrow, e.g. 30"]
  location          varchar(255)  [null, note: "Pickup address for the book"]
  latitude          decimal(10,7) [null, note: "Book pickup GPS latitude for distance calculation"]
  longitude         decimal(10,7) [null, note: "Book pickup GPS longitude for distance calculation"]
  availability      varchar(20)   [default: 'available', note: "Enum: available | borrowed | unavailable"]
  avg_rating        decimal(3,2)  [default: 0.00, note: "Computed average from reviews on this book"]
  is_active         boolean       [default: true, note: "Soft delete; false = removed from listings"]
  created_at        timestamp     [default: `now()`]
  updated_at        timestamp     [default: `now()`]

  Note: "Physical books listed for community sharing. Uploaded via the Upload Book modal."
}

Table borrow_requests {
  id              int        [pk, increment]
  book_id         int        [not null, ref: > books.id, note: "The book being borrowed"]
  borrower_id     int        [not null, ref: > users.id, note: "User who requested to borrow"]
  status          varchar(30) [not null, default: 'pending', note: "Enum: pending | approved | active | returned | cancelled"]
  requested_at    timestamp  [default: `now()`, note: "When the borrow request was submitted"]
  approved_at     timestamp  [null, note: "When the owner approved the request"]
  borrowed_at     timestamp  [null, note: "When the borrower physically picked up the book"]
  due_date        timestamp  [null, note: "Return deadline (borrowed_at + borrow_duration_days)"]
  returned_at     timestamp  [null, note: "When borrower marked as returned"]
  confirmed_at    timestamp  [null, note: "When owner confirmed receipt of returned book"]

  Note: "Tracks the full lifecycle of a book loan. Powers Borrowed and Lent Out profile tabs."
}

Table reviews {
  id                  int        [pk, increment]
  borrow_request_id   int        [not null, ref: > borrow_requests.id, note: "Review tied to a specific loan"]
  reviewer_id         int        [not null, ref: > users.id, note: "User who wrote the review"]
  reviewee_id         int        [not null, ref: > users.id, note: "User being reviewed (lender/borrower)"]
  book_id             int        [not null, ref: > books.id, note: "Book involved in the transaction"]
  rating              decimal(3,2) [not null, note: "Star rating, e.g. 4.8 out of 5"]
  review_text         text       [null, note: "Written review body visible in Community Ratings section"]
  created_at          timestamp  [default: `now()`]

  Note: "Community Ratings. Borrowers review lenders; visible on Book Details and user profiles."
}

Table wishlist {
  id         int       [pk, increment]
  user_id    int       [not null, ref: > users.id, note: "User who saved the book"]
  book_id    int       [not null, ref: > books.id, note: "Book that was saved/favourited"]
  created_at timestamp [default: `now()`]

  indexes {
    (user_id, book_id) [unique, name: "uq_wishlist_user_book"]
  }

  Note: "Many-to-many join for the Wishlist tab on the Profile screen (heart icon)."
}

Table conversations {
  id              int       [pk, increment]
  participant_1   int       [not null, ref: > users.id, note: "One side of the conversation (typically the requester)"]
  participant_2   int       [not null, ref: > users.id, note: "Other side (typically the book owner)"]
  book_id         int       [null, ref: > books.id, note: "Book the conversation is about (optional context)"]
  last_message_at timestamp [null, note: "Denormalized for sorting the conversation list"]
  created_at      timestamp [default: `now()`]

  indexes {
    (participant_1, participant_2, book_id) [name: "idx_conversation_participants_book"]
  }

  Note: "Chat thread between two users. Triggered from the CHAT button on a Book Details page."
}

Table messages {
  id              int        [pk, increment]
  conversation_id int        [not null, ref: > conversations.id, note: "Parent conversation thread"]
  sender_id       int        [not null, ref: > users.id, note: "User who sent the message"]
  body            text       [not null, note: "The message content"]
  is_read         boolean    [default: false, note: "Used for Unread/Archive filters in Chat screen"]
  is_archived     boolean    [default: false, note: "Supports the Archive tab in the Chat screen"]
  sent_at         timestamp  [default: `now()`]

  Note: "Individual messages within a conversation. Visible in the Chat / Message screen."
}

// =============================================
// RELATIONSHIP SUMMARY (DBDiagram Ref block)
// =============================================
// All refs already inline above. Listed here for clarity:

// users.id       <  user_settings.user_id        (1:1)
// users.id       <  books.owner_id               (1:many — a user uploads many books)
// genres.id      <  books.genre_id               (1:many — genre has many books)
// books.id       <  borrow_requests.book_id      (1:many — a book can be requested many times over time)
// users.id       <  borrow_requests.borrower_id  (1:many — user can borrow many books)
// borrow_requests.id < reviews.borrow_request_id (1:1   — one review per loan transaction)
// users.id       <  reviews.reviewer_id          (1:many)
// users.id       <  reviews.reviewee_id          (1:many)
// books.id       <  reviews.book_id              (1:many)
// users.id       <  wishlist.user_id             (1:many)
// books.id       <  wishlist.book_id             (1:many)
// users.id       <  conversations.participant_1  (1:many)
// users.id       <  conversations.participant_2  (1:many)
// books.id       <  conversations.book_id        (1:many)
// conversations.id < messages.conversation_id   (1:many)
// users.id       <  messages.sender_id           (1:many)
```

---

## 📌 Design Notes & Decisions

| Topic | Decision |
|---|---|
| **Author as free text** | The Upload Book form has a plain text "Author Name" field — no separate `authors` table is warranted unless the app needs an Author browsing page (nav bar shows "Author" link, but no Author detail screen exists in the provided mockups). Flagged for potential future extraction. |
| **Location on both user & book** | Users have a profile address (for their pickup point) and books have an independent address (where the book physically is). The GPS lat/lon on both enable the "Books Near You" and distance badge features. |
| **credits column** | The coin icon (🪙 120) on the Profile screen represents a gamification/reputation credit system. Stored on the user; the mechanism for earning/spending is not shown in the mockups but must be tracked here. |
| **avg_rating denormalization** | `avg_rating` on both `users` and `books` is a denormalized computed column — updated via trigger or background job whenever a new review is submitted, for performance. |
| **borrow_request status enum** | `pending → approved → active → returned → cancelled`. The "Return in 5 days" countdown is derived from `due_date - now()`. "Mark as Returned" sets `returned_at`; "Confirm Received" sets `confirmed_at`. |
| **reviews dual FK** | `reviewer_id` + `reviewee_id` allows reviews to be for lenders OR borrowers. The "Community Ratings" tab on a user profile shows reviews where `reviewee_id = that user`. |
| **conversations.book_id nullable** | Most chats are about a book, but the platform could support general user-to-user messaging, so the FK is nullable. |
| **user_settings 1:1** | Separated from users to avoid a wide table; allows future expansion of preference fields without altering the core users table. |
| **Password reset** | The Forgot Password / Verify Code / Set New Password flow implies a `password_reset_tokens` table (one-time token, expiry), but it is not shown as a persistent entity in the UI, so it is omitted from the primary ERD. Add it if implementing auth backend. |
