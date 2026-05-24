# BookBuddy API Documentation - Chat Module

This document outlines the REST APIs and WebSocket endpoints for the BookBuddy platform's messaging functionality. It is designed for frontend developers integrating the chat module.

> [!NOTE]
> All REST endpoints require authentication and expect a standard `Authorization: Bearer <token>` header. The WebSocket endpoint expects a `?token=<token>` query parameter.

---

## 1. REST Endpoints
**Base Path:** `/conversations`

### 1.1 List Conversations
**`GET /conversations`**
Get your conversation list with last message preview and unread count. Supports filtering for different tabs: All, Unread, Archive.
Sorted by most recent message.

**Query Parameters:**
- `filter_type` (str, default: "all"): Filter conversations ("all", "unread", "archive").
- `other_user_id` (int, optional): Filter conversations by a specific user ID.
- `page` (int, default: 1): Page number.
- `per_page` (int, default: 20): Items per page.

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "other_user": {
        "id": 2,
        "full_name": "John Doe",
        "avatar_url": "http://..."
      },
      "book_id": 5,
      "book_title": "A Tale of Love and Darkness",
      "book_image": "http://...",
      "last_message": "Hi, is this book still available?",
      "last_message_at": "2026-05-24T10:00:00Z",
      "unread_count": 2,
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

### 1.2 Get Unread Message Count
**`GET /conversations/unread-count`**
Get total number of unread messages across all conversations (useful for notification bell badge).

**Response:**
```json
{
  "unread_count": 5
}
```

### 1.3 Get Conversation Details
**`GET /conversations/user/{other_user_id}`**
Get details of a specific conversation with another user.

**Path Parameters:**
- `other_user_id` (int, required)

**Response:** Conversation Object (Same structure as 1.1 items)

### 1.4 Get Messages
**`GET /conversations/user/{other_user_id}/messages`**
Get messages with another user, ordered newest first. Also implicitly marks messages as read.

**Path Parameters:**
- `other_user_id` (int, required)

**Query Parameters:** 
- `page` (int, default: 1)
- `per_page` (int, default: 50)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "conversation_id": 1,
      "sender": { "id": 2, "full_name": "John Doe", "avatar_url": "..." },
      "receiver": { "id": 1, "full_name": "Alice", "avatar_url": "..." },
      "body": "Yes, it is!",
      "is_read": true,
      "sent_at": "2026-05-24T10:05:00Z"
    }
  ],
  "book_id": 5,
  "book_title": "A Tale of Love and Darkness",
  "book_image": "http://...",
  "total": 10,
  "page": 1,
  "per_page": 50,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

### 1.5 Send a Message
**`POST /conversations/user/{other_user_id}/messages`**
Send a new message to another user. Auto-creates conversation if it doesn't exist.

**Path Parameters:**
- `other_user_id` (int, required)

**Payload (JSON):**
```json
{
  "body": "Sure, how about 3 PM?"
}
```

**Response:** Single Message Object (Same structure as 1.4 items)

### 1.6 Mark Messages as Read
**`PATCH /conversations/user/{other_user_id}/read`**
Mark all unread messages from the other user as read. (Usually done automatically when fetching messages, but can be done manually).

**Response:** HTTP 200 OK

### 1.7 Archive Conversation
**`PATCH /conversations/user/{other_user_id}/archive`**
Move a conversation to the Archive tab.

**Response:** HTTP 200 OK

---

## 2. WebSocket Events

Connect to the WebSocket endpoint to receive real-time messages and conversation updates. 

**Connection URL:** 
`ws://<domain>/conversations/?token=<your_auth_token>`

> [!IMPORTANT]
> The WebSocket connection requires the authentication token to be passed as a query parameter (`token=...`), NOT in the headers.

### 2.1 Incoming Events (Server to Client)

When a message is received or the conversation list changes, the server will push JSON objects to the client.

#### A. Receive a New Message
Triggered when someone sends you a message.
```json
{
  "event": "RECEIVE_MESSAGE",
  "data": {
    "id": 15,
    "conversation_id": 1,
    "sender": null, 
    "receiver": { "id": 2, "full_name": "John Doe", "avatar_url": "..." },
    "body": "Hello!",
    "is_read": false,
    "sent_at": "2026-05-24T10:05:00Z"
  }
}
```

#### B. Conversation List Update
Triggered upon connecting, and also when an action happens that updates conversation sorting or unread counts (like receiving a message or marking messages as read).
```json
{
  "event": "CONVERSATION_LIST_UPDATE",
  "data": [
    {
      "id": 1,
      "other_user": { "id": 2, "full_name": "John Doe", "avatar_url": "..." },
      "last_message": "Hello!",
      "unread_count": 1,
      "last_message_at": "2026-05-24T10:05:00Z"
    }
  ]
}
```

### 2.2 Outgoing Events (Client to Server)

You can send JSON messages to the WebSocket server to trigger specific actions.

#### A. Mark Messages as Read
When the user views a chat, send this to tell the server to mark messages from that user as read and broadcast an updated unread count.
```json
{
  "action": "mark_read",
  "other_user_id": 2
}
```

> [!TIP]
> **Implementation Note:** 
> When the user sends a new message (using `POST /conversations/user/{id}/messages`), the message will NOT be echoed back via WebSocket to the sender. The sender's frontend should append the newly sent message directly to the UI using the response of the `POST` request.
