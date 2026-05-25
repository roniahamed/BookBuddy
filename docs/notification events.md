# BookBuddy Notification Events

Based on the codebase analysis, here is the comprehensive list of actions and events that trigger notifications in the BookBuddy project. Notifications are delivered via **In-App Notifications**, **FCM Push Notifications**, and/or **Emails**.

## 1. Borrowing Lifecycle Notifications
*Found in `app/modules/borrowing/service.py`*

- **Borrow Request Created**
  - **Trigger:** A user requests to borrow a book.
  - **Recipient:** Book Owner
  - **Method:** In-App Notification
  - **Message:** "[User] has requested to borrow your book '[Book Title]'."
- **Borrow Request Approved**
  - **Trigger:** Book owner approves a pending borrow request.
  - **Recipient:** Borrower
  - **Method:** In-App Notification
  - **Message:** "Your request to borrow '[Book Title]' has been approved! Due date: [Date]."
- **Borrow Request Rejected**
  - **Trigger:** Book owner rejects a pending borrow request.
  - **Recipient:** Borrower
  - **Method:** In-App Notification
  - **Message:** "Your request to borrow '[Book Title]' was rejected by the owner."
- **Borrow Request Cancelled**
  - **Trigger:** Borrower cancels their pending request before approval.
  - **Recipient:** Book Owner
  - **Method:** In-App Notification
  - **Message:** "[User] has cancelled their request to borrow '[Book Title]'."
- **Book Marked as Returned**
  - **Trigger:** Borrower marks the book as returned in the app.
  - **Recipient:** Book Owner
  - **Method:** In-App Notification
  - **Message:** "[User] has marked '[Book Title]' as returned. Please confirm receipt."
- **Book Return Confirmed**
  - **Trigger:** Book owner confirms they have received the book back.
  - **Recipient:** Borrower
  - **Method:** In-App Notification + Push Notification
  - **Message:** "The owner confirmed the return of '[Book Title]'. You earned [X] credits!"

## 2. Books & Reviews Notifications
*Found in `app/modules/books/service.py`*

- **New Book Uploaded**
  - **Trigger:** A user uploads a new book that requires approval.
  - **Recipient:** All Admin Users
  - **Method:** In-App Notification + Push Notification
  - **Message:** "New Book Uploaded: '[Book Title]' needs approval."
- **New Review Received**
  - **Trigger:** A user leaves a review after a completed borrow transaction.
  - **Recipient:** The reviewed user (can be the owner or the borrower).
  - **Method:** In-App Notification
  - **Message:** "[User] has left a [X]-star review for '[Book Title]'."

## 3. Chat Notifications
*Found in `app/modules/chat/service.py`*

- **New Chat Message**
  - **Trigger:** A user sends a direct message to another user.
  - **Recipient:** Message receiver
  - **Method:** Push Notification
  - **Message:** "New message from [User]" (with message preview).

## 4. Automated Scheduled Notifications
*Found in `app/background/tasks.py`*

- **Overdue Book Warning**
  - **Trigger:** Every 6 hours, the system checks for active borrows past their due date.
  - **Recipient:** Borrower & Book Owner
  - **Method:** Push Notification (Both) + Email Notification (Borrower only)
  - **Message to Borrower:** '"{Book Title}" is overdue. Please return it as soon as possible.'
  - **Message to Owner:** '"{Book Title}" lent to [Borrower] is overdue.'
- **Due Date Reminders**
  - **Trigger:** Daily at 9:00 AM UTC, reminds users of books due in X days (default 2).
  - **Recipient:** Borrower
  - **Method:** Push Notification + Email Notification
  - **Message:** '"{Book Title}" is due in [X] day(s). Please plan your return.'

## 5. Admin & Moderation Notifications
*Found in `app/modules/admin/service.py`*

- **Account Suspended**
  - **Trigger:** Admin suspends a user's account.
  - **Recipient:** Suspended User
  - **Method:** Push Notification + Email Notification
  - **Message:** Custom reason provided by admin, or "Your account has been suspended. Please contact support."
- **Account Reactivated**
  - **Trigger:** Admin reactivates a suspended user's account.
  - **Recipient:** Reactivated User
  - **Method:** Push Notification + Email Notification
  - **Message:** "Great news! Your BookBuddy account has been reactivated. Welcome back!"
- **Book Approved**
  - **Trigger:** Admin approves a pending book listing.
  - **Recipient:** Book Owner
  - **Method:** Push Notification + Email Notification
  - **Message:** "Your uploaded book '[Book Title]' has been approved and is now visible to the community!"
- **Book Rejected**
  - **Trigger:** Admin rejects a pending book listing.
  - **Recipient:** Book Owner
  - **Method:** Push Notification + Email Notification
  - **Message:** "Your uploaded book '[Book Title]' was rejected and will not be displayed on the platform."
- **Book Listing Removed (Deleted)**
  - **Trigger:** Admin deletes a book listing for policy violations.
  - **Recipient:** Book Owner
  - **Method:** Push Notification + Email Notification
  - **Message:** "Your book listing '[Book Title]' has been removed by an admin for policy violations."
- **Book Marked Unavailable**
  - **Trigger:** Admin manually marks an available book as unavailable.
  - **Recipient:** Book Owner
  - **Method:** Push Notification + Email Notification
  - **Message:** "Your book '[Book Title]' has been marked unavailable by an admin."
- **Admin Broadcast Message**
  - **Trigger:** Admin sends a broadcast notification from the dashboard.
  - **Recipient:** Specific User or All Active Users
  - **Method:** Push Notification + Email Notification
  - **Message:** Custom title and body defined by the admin.
