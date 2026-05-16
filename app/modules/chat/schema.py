"""
Chat module Pydantic schemas.

Covers: Conversation list (All/Unread/Archive tabs), message view.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Participants ────────────────────────────────────────
class ChatUserBrief(BaseModel):
    """Participant info shown in conversation list."""
    id: int
    full_name: str
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Conversation ────────────────────────────────────────
class ConversationResponse(BaseModel):
    """Single conversation in the chat list."""
    id: int
    other_user: Optional[ChatUserBrief] = None
    book_id: Optional[int] = None
    book_title: Optional[str] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """Paginated conversation list."""
    items: List[ConversationResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class ConversationCreateRequest(BaseModel):
    """Start a new conversation (CHAT button on Book Details)."""
    participant_id: int = Field(..., description="ID of the other user")
    book_id: Optional[int] = Field(None, description="ID of the book (optional context)")
    initial_message: Optional[str] = Field(None, description="First message to send")

    model_config = {"json_schema_extra": {
        "example": {
            "participant_id": 2,
            "book_id": 1,
            "initial_message": "Hi! Is A Tale of Love and Darkness still available?",
        }
    }}


# ─── Message ─────────────────────────────────────────────
class MessageResponse(BaseModel):
    """Single message in conversation view."""
    id: int
    sender: Optional[ChatUserBrief] = None
    body: str
    is_read: bool = False
    sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    """Paginated messages."""
    items: List[MessageResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 50
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class MessageCreateRequest(BaseModel):
    """Send a new message in a conversation."""
    body: str = Field(..., min_length=1, description="Message content")

    model_config = {"json_schema_extra": {
        "example": {"body": "Sure, how about 3 PM at Dizengoff St?"}
    }}


class UnreadCountResponse(BaseModel):
    """Total unread message count (notification badge)."""
    unread_count: int = 0
