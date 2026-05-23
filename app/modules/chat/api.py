"""
Chat module API endpoints.

Covers:
- GET    /conversations                  — List conversations (All/Unread/Archive)
- POST   /conversations                  — Start new conversation (CHAT button)
- GET    /conversations/unread-count     — Total unread count (notification badge)
- GET    /conversations/{id}             — Conversation details
- GET    /conversations/{id}/messages    — Messages in conversation
- POST   /conversations/{id}/messages    — Send message
- PATCH  /conversations/{id}/read        — Mark all messages as read
- PATCH  /conversations/{id}/archive     — Archive conversation
"""
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.modules.auth.dependencies import get_current_user, get_current_user_ws
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
    other_user_id: int | None = Query(None, description="Filter conversations by a specific user ID"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.list_conversations(current_user, filter_type, pagination, other_user_id)


# Start a conversation endpoint removed since it's dynamically created by send_message


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
    "/user/{other_user_id}",
    response_model=ConversationResponse,
    summary="Get conversation details",
    description="Get details of a specific conversation with another user.",
    responses={
        404: {"description": "Conversation not found"},
    },
)
async def get_conversation(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.get_conversation(other_user_id, current_user)


@router.get(
    "/user/{other_user_id}/messages",
    response_model=MessageListResponse,
    summary="Get messages",
    description=(
        "Get messages with another user, ordered newest first (paginated). "
        "Each message includes sender info and read status."
    ),
)
async def get_messages(
    other_user_id: int,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    service.mark_read(other_user_id, current_user)
    return service.get_messages(other_user_id, current_user, pagination)


@router.post(
    "/user/{other_user_id}/messages",
    response_model=MessageResponse,
    summary="Send a message",
    description=(
        "Send a new message to another user. Auto-creates conversation if it doesn't exist. "
        "Updates the conversation's last_message_at for sorting."
    ),
    responses={
        404: {"description": "User not found"},
    },
)
async def send_message(
    other_user_id: int,
    data: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    msg = service.send_message(other_user_id, current_user, data)

    # We do NOT send new_message to the sender's websocket.

    # Send via websocket to recipient
    try:
        if other_user_id:
            recipient = db.query(User).filter(User.id == other_user_id).first()
            if recipient:
                recipient_convs = service.list_conversations(recipient, "all", PaginationParams(page=1, per_page=20))
                
                # For the recipient, the sender is "other user" so it maps to receiver
                recipient_msg = MessageResponse(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    sender=None,
                    receiver=msg.sender,
                    body=msg.body,
                    is_read=msg.is_read,
                    sent_at=msg.sent_at
                )

                await manager.send_to_user({
                    "event": "RECEIVE_MESSAGE",
                    "data": recipient_msg.model_dump(mode="json")
                }, recipient.id)
                
                await manager.send_to_user({
                    "event": "CONVERSATION_LIST_UPDATE",
                    "data": recipient_convs.model_dump(mode="json")["items"]
                }, recipient.id)
    except Exception:
        pass

    return msg


@router.patch(
    "/user/{other_user_id}/read",
    summary="Mark messages as read",
    description="Mark all unread messages from the other user as read.",
)
async def mark_read(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.mark_read(other_user_id, current_user)


@router.patch(
    "/user/{other_user_id}/archive",
    summary="Archive conversation",
    description="Move a conversation to the Archive tab.",
    responses={
        404: {"description": "Conversation not found"},
    },
)
async def archive_conversation(
    other_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ChatService(db)
    return service.archive_conversation(other_user_id, current_user)

# ─── WebSocket Endpoint ──────────────────────────────────

class ConnectionManager:
    def __init__(self):
        # Maps user_id to list of active WebSockets
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

@router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    
    current_user = await get_current_user_ws(token, db)
    if not current_user:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, current_user.id)
    
    # Send initial user list (latest 20 conversations)
    try:
        service = ChatService(db)
        convs = service.list_conversations(current_user, "all", PaginationParams(page=1, per_page=20))
        await manager.send_to_user({
            "event": "CONVERSATION_LIST_UPDATE",
            "data": convs.model_dump(mode="json")["items"]
        }, current_user.id)
    except Exception:
        pass

    try:
        while True:
            text = await websocket.receive_text()
            try:
                import json
                data = json.loads(text)
                if data.get("action") == "mark_read":
                    other_user_id = data.get("other_user_id")
                    if other_user_id is not None:
                        service = ChatService(db)
                        service.mark_read(int(other_user_id), current_user)
                        
                        # Send updated conversation list to reflect the new unread count
                        convs = service.list_conversations(current_user, "all", PaginationParams(page=1, per_page=20))
                        await manager.send_to_user({
                            "event": "CONVERSATION_LIST_UPDATE",
                            "data": convs.model_dump(mode="json")["items"]
                        }, current_user.id)
            except json.JSONDecodeError:
                pass
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, current_user.id)
