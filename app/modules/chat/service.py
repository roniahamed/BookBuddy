"""
Chat module service — business logic for conversations and encrypted messaging.
"""
import math
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.modules.chat.repository import ChatRepository
from app.modules.chat.schema import (
    ConversationResponse, ConversationListResponse, ConversationCreateRequest,
    MessageResponse, MessageListResponse, MessageCreateRequest,
    ChatUserBrief, UnreadCountResponse,
)
from app.modules.users.model import User
from app.shared.pagination import PaginationParams


class ChatService:
    """Handles chat business logic with encrypted messaging."""

    def __init__(self, db: Session):
        self.repo = ChatRepository(db)
        self.db = db

    def _get_participants(self, conv, current_user_id: int):
        if conv.participant_1 == current_user_id:
            current = conv.participant_1_user
            other = conv.participant_2_user
        else:
            current = conv.participant_2_user
            other = conv.participant_1_user
            
        me = ChatUserBrief(id=current.id, full_name=current.full_name, avatar_url=current.avatar_url) if current else None
        other_user = ChatUserBrief(id=other.id, full_name=other.full_name, avatar_url=other.avatar_url) if other else None
        return me, other_user

    def list_conversations(
        self, user: User, filter_type: str, pagination: PaginationParams, other_user_id: int = None
    ) -> ConversationListResponse:
        results, total = self.repo.get_conversations(
            user.id, filter_type, pagination.offset, pagination.per_page, other_user_id
        )

        items = []
        for r in results:
            conv = r["conversation"]
            me, other_user = self._get_participants(conv, user.id)
            items.append(ConversationResponse(
                id=conv.id,
                other_user=other_user,
                book_id=conv.book_id,
                book_title=conv.book.title if conv.book else None,
                book_image=conv.book.front_cover_image if conv.book else None,
                last_message=r["last_message"],  # Already decrypted in repo
                last_message_at=conv.last_message_at,
                unread_count=r["unread_count"],
                created_at=conv.created_at,
            ))

        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return ConversationListResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    # create_conversation removed as send_message handles it dynamically

    def get_conversation(self, other_user_id: int, user: User) -> ConversationResponse:
        conv = self.repo.find_existing_conversation(user.id, other_user_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        me, other_user = self._get_participants(conv, user.id)
        return ConversationResponse(
            id=conv.id,
            other_user=other_user,
            book_id=conv.book_id,
            book_title=conv.book.title if conv.book else None,
            book_image=conv.book.front_cover_image if conv.book else None,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
        )

    def get_messages(self, other_user_id: int, user: User, pagination: PaginationParams) -> MessageListResponse:
        conv = self.repo.find_existing_conversation(user.id, other_user_id)
        if not conv:
            return MessageListResponse(
                items=[], 
                total=0, page=pagination.page,
                per_page=pagination.per_page, pages=0,
                has_next=False, has_prev=False
            )

        # Returns decrypted message dicts
        messages, total = self.repo.get_messages(conv.id, pagination.offset, pagination.per_page)

        current_user_brief = ChatUserBrief(id=user.id, full_name=user.full_name, avatar_url=user.avatar_url)
        other_user_model = conv.participant_2_user if conv.participant_1 == user.id else conv.participant_1_user
        other_user_brief = ChatUserBrief(id=other_user_model.id, full_name=other_user_model.full_name, avatar_url=other_user_model.avatar_url) if other_user_model else None

        items = []
        for m in messages:
            msg_sender = None
            msg_receiver = None
            if m["sender"]:
                if m["sender"].id == user.id:
                    msg_sender = current_user_brief
                    msg_receiver = None
                else:
                    msg_sender = None
                    msg_receiver = other_user_brief

            items.append(MessageResponse(
                id=m["id"],
                conversation_id=conv.id,
                sender=msg_sender,
                receiver=msg_receiver,
                body=m["body"],  # Decrypted plaintext
                is_read=m["is_read"],
                sent_at=m["sent_at"],
            ))

        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return MessageListResponse(
            items=items, 
            book_id=conv.book_id,
            book_title=conv.book.title if conv.book else None,
            book_image=conv.book.front_cover_image if conv.book else None,
            total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def send_message(self, other_user_id: int, user: User, data: MessageCreateRequest) -> MessageResponse:
        conv = self.repo.find_existing_conversation(user.id, other_user_id)
        if not conv:
            # Check if other_user exists
            other_user = self.db.query(User).filter(User.id == other_user_id).first()
            if not other_user:
                raise HTTPException(status_code=404, detail=f"User with id={other_user_id} not found")
            conv = self.repo.create_conversation(user.id, other_user_id)

        result = self.repo.send_message(conv.id, user.id, data.body)

        # Send push notification to recipient
        recipient_id = conv.participant_2 if conv.participant_1 == user.id else conv.participant_1
        recipient_user = conv.participant_2_user if conv.participant_1 == user.id else conv.participant_1_user
        self._notify_new_message(recipient_id, user.full_name, data.body)

        return MessageResponse(
            id=result["id"],
            conversation_id=conv.id,
            sender=ChatUserBrief(id=user.id, full_name=user.full_name, avatar_url=user.avatar_url),
            receiver=None,
            body=result["body"],  # Plaintext returned to sender
            is_read=False,
            sent_at=result["sent_at"],
        )

    def mark_read(self, other_user_id: int, user: User) -> dict:
        conv = self.repo.find_existing_conversation(user.id, other_user_id)
        if not conv:
            return {"message": "No conversation found"}

        count = self.repo.mark_messages_read(conv.id, user.id)
        return {"message": f"Marked {count} messages as read"}

    def archive_conversation(self, other_user_id: int, user: User) -> dict:
        conv = self.repo.find_existing_conversation(user.id, other_user_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        self.repo.archive_conversation(conv.id, user.id)
        return {"message": "Conversation archived"}

    def get_unread_count(self, user: User) -> UnreadCountResponse:
        count = self.repo.get_total_unread_count(user.id)
        return UnreadCountResponse(unread_count=count)

    def _notify_new_message(self, recipient_id: int, sender_name: str, message_preview: str):
        """Send push notification for new message via Celery."""
        try:
            recipient = self.db.query(User).filter(User.id == recipient_id).first()
            if recipient:
                from app.background.tasks import send_push_notification_task
                preview = message_preview[:100] + "..." if len(message_preview) > 100 else message_preview
                send_push_notification_task.delay(
                    recipient.id,
                    f"New message from {sender_name}",
                    preview,
                )
        except Exception:
            pass  # Non-critical, don't fail the message send
