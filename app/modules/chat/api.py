"""
Chat module API endpoints.

Covers:
- GET    /conversations                  — List conversations (All/Unread/Archive)
- POST   /conversations                  — Start new conversation (CHAT button)
- GET    /conversations/unread-count     — Total unread count (notification badge)
- GET    /conversations/{id}             — Conversation details
- GET    /conversations/{id}/messages    — Messages in conversation
- POST   /conversations/{id}/messages    — Send message
- PUT    /conversations/{id}/read        — Mark all messages as read
- PUT    /conversations/{id}/archive     — Archive conversation
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.users.model import User
from app.modules.chat.service import ChatService
from app.modules.chat.schema import (
    ConversationResponse, ConversationListResponse, ConversationCreateRequest,
    MessageResponse, MessageListResponse, MessageCreateRequest,
    UnreadCountResponse,
)
from app.shared.pagination import PaginationParams

router = APIRouter()


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List conversations",
    description=(
        "Get your conversation list with last message preview and unread count. "
        "Supports filtering by: 'all' (All Message tab), 'unread' (Unread tab), "
        "'archive' (Archive tab). Sorted by most recent message."
    ),
)
async def list_conversations(
    filter_type: str = Query("all", description="Filter: all | unread | archive"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.list_conversations(current_user, filter_type, pagination)


@router.post(
    "",
    response_model=ConversationResponse,
    summary="Start a conversation",
    description=(
        "Start a new conversation with a user (CHAT button on Book Details). "
        "If a conversation already exists between the two users about the same book, "
        "it returns the existing conversation. Optionally send an initial message."
    ),
    responses={
        400: {"description": "Cannot chat with yourself"},
        404: {"description": "User not found"},
    },
)
async def create_conversation(
    data: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.create_conversation(current_user, data)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread message count",
    description="Get total number of unread messages across all conversations (notification bell badge).",
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.get_unread_count(current_user)


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation details",
    description="Get details of a specific conversation including participant info.",
    responses={
        403: {"description": "Not a participant"},
        404: {"description": "Conversation not found"},
    },
)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.get_conversation(conversation_id, current_user)


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
    summary="Get messages",
    description=(
        "Get messages in a conversation, ordered newest first (paginated). "
        "Each message includes sender info and read status."
    ),
    responses={
        403: {"description": "Not a participant"},
        404: {"description": "Conversation not found"},
    },
)
async def get_messages(
    conversation_id: int,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.get_messages(conversation_id, current_user, pagination)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    summary="Send a message",
    description=(
        "Send a new message in a conversation. "
        "Updates the conversation's last_message_at for sorting."
    ),
    responses={
        403: {"description": "Not a participant"},
        404: {"description": "Conversation not found"},
    },
)
async def send_message(
    conversation_id: int,
    data: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.send_message(conversation_id, current_user, data)


@router.put(
    "/{conversation_id}/read",
    summary="Mark messages as read",
    description="Mark all unread messages from the other user as read.",
    responses={
        403: {"description": "Not a participant"},
        404: {"description": "Conversation not found"},
    },
)
async def mark_read(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.mark_read(conversation_id, current_user)


@router.put(
    "/{conversation_id}/archive",
    summary="Archive conversation",
    description="Move a conversation to the Archive tab.",
    responses={
        403: {"description": "Not a participant"},
        404: {"description": "Conversation not found"},
    },
)
async def archive_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.archive_conversation(conversation_id, current_user)
