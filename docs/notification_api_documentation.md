# BookBuddy API Documentation - Notification Module

This document outlines the REST APIs for the BookBuddy platform's notification system, covering in-app notifications and notification preferences. It is designed for frontend developers integrating the notification module.

> [!NOTE]
> All endpoints require authentication and expect a standard `Authorization: Bearer <token>` header.

---

## 1. REST Endpoints
**Base Path:** `/notifications`

### 1.1 List Notifications
**`GET /notifications`**
Get the authenticated user's in-app notifications (e.g., borrow requests, review submissions, system alerts).

**Query Parameters:**
- `page` (int, default: 1): Page number.
- `per_page` (int, default: 20): Items per page.

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "title": "New Borrow Request",
      "message": "John Doe requested to borrow 'A Tale of Love and Darkness'.",
      "is_read": false,
      "created_at": "2026-05-24T10:00:00Z"
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

### 1.2 Get Notification Details
**`GET /notifications/{notification_id}`**
Get details of a specific notification.

**Path Parameters:**
- `notification_id` (int, required)

**Response:**
```json
{
  "id": 1,
  "title": "New Borrow Request",
  "message": "John Doe requested to borrow 'A Tale of Love and Darkness'.",
  "is_read": true,
  "created_at": "2026-05-24T10:00:00Z"
}
```

### 1.3 Mark All Notifications as Read
**`PATCH /notifications/read-all`**
Mark all unread notifications for the current user as read.

**Response:** HTTP 200 OK

### 1.4 Get Notification Preferences
**`GET /notifications/preferences`**
Get current notification settings (Email notifications and new message alerts). Corresponds to the notification toggles on the Settings screen.

**Response:**
```json
{
  "email_notifications": true,
  "new_message_alert": true
}
```

### 1.5 Update Notification Preferences
**`PATCH /notifications/preferences`**
Update notification settings. Only provided fields are updated. Controls Email Notification and New Message Alert toggles.

**Payload (JSON):**
```json
{
  "email_notifications": false,
  "new_message_alert": true
}
```

**Response:**
```json
{
  "email_notifications": false,
  "new_message_alert": true
}
```
