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

    def _get_other_user(self, conv, current_user_id: int) -> ChatUserBrief | None:
        if conv.participant_1 == current_user_id:
            user = conv.participant_2_user
        else:
            user = conv.participant_1_user
        if user:
            return ChatUserBrief(id=user.id, full_name=user.full_name, avatar_url=user.avatar_url)
        return None

    def list_conversations(
        self, user: User, filter_type: str, pagination: PaginationParams
    ) -> ConversationListResponse:
        results, total = self.repo.get_conversations(
            user.id, filter_type, pagination.offset, pagination.per_page
        )

        items = []
        for r in results:
            conv = r["conversation"]
            items.append(ConversationResponse(
                id=conv.id,
                other_user=self._get_other_user(conv, user.id),
                book_id=conv.book_id,
                book_title=conv.book.title if conv.book else None,
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

    def create_conversation(self, user: User, data: ConversationCreateRequest) -> ConversationResponse:
        if data.participant_id == user.id:
            raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself")

        other_user = self.db.query(User).filter(User.id == data.participant_id).first()
        if not other_user:
            raise HTTPException(status_code=404, detail="User not found")

        existing = self.repo.find_existing_conversation(user.id, data.participant_id, data.book_id)
        if existing:
            conv = self.repo.get_conversation_by_id(existing.id)
            if data.initial_message:
                self.repo.send_message(conv.id, user.id, data.initial_message)
                # Send push notification via Celery
                self._notify_new_message(data.participant_id, user.full_name, data.initial_message)

            return ConversationResponse(
                id=conv.id,
                other_user=self._get_other_user(conv, user.id),
                book_id=conv.book_id,
                book_title=conv.book.title if conv.book else None,
                last_message=data.initial_message,
                last_message_at=conv.last_message_at,
                unread_count=0,
                created_at=conv.created_at,
            )

        conv = self.repo.create_conversation(user.id, data.participant_id, data.book_id)
        conv = self.repo.get_conversation_by_id(conv.id)

        if data.initial_message:
            self.repo.send_message(conv.id, user.id, data.initial_message)
            self._notify_new_message(data.participant_id, user.full_name, data.initial_message)

        return ConversationResponse(
            id=conv.id,
            other_user=self._get_other_user(conv, user.id),
            book_id=conv.book_id,
            book_title=conv.book.title if conv.book else None,
            last_message=data.initial_message,
            last_message_at=conv.last_message_at,
            unread_count=0,
            created_at=conv.created_at,
        )

    def get_conversation(self, conv_id: int, user: User) -> ConversationResponse:
        conv = self.repo.get_conversation_by_id(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.participant_1 != user.id and conv.participant_2 != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return ConversationResponse(
            id=conv.id,
            other_user=self._get_other_user(conv, user.id),
            book_id=conv.book_id,
            book_title=conv.book.title if conv.book else None,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
        )

    def get_messages(self, conv_id: int, user: User, pagination: PaginationParams) -> MessageListResponse:
        conv = self.repo.get_conversation_by_id(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.participant_1 != user.id and conv.participant_2 != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Returns decrypted message dicts
        messages, total = self.repo.get_messages(conv_id, pagination.offset, pagination.per_page)

        items = [
            MessageResponse(
                id=m["id"],
                sender=ChatUserBrief(id=m["sender"].id, full_name=m["sender"].full_name, avatar_url=m["sender"].avatar_url) if m["sender"] else None,
                body=m["body"],  # Decrypted plaintext
                is_read=m["is_read"],
                sent_at=m["sent_at"],
            )
            for m in messages
        ]

        pages = math.ceil(total / pagination.per_page) if pagination.per_page > 0 else 0
        return MessageListResponse(
            items=items, total=total, page=pagination.page,
            per_page=pagination.per_page, pages=pages,
            has_next=pagination.page < pages, has_prev=pagination.page > 1,
        )

    def send_message(self, conv_id: int, user: User, data: MessageCreateRequest) -> MessageResponse:
        conv = self.repo.get_conversation_by_id(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.participant_1 != user.id and conv.participant_2 != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        result = self.repo.send_message(conv_id, user.id, data.body)

        # Send push notification to recipient
        recipient_id = conv.participant_2 if conv.participant_1 == user.id else conv.participant_1
        self._notify_new_message(recipient_id, user.full_name, data.body)

        return MessageResponse(
            id=result["id"],
            sender=ChatUserBrief(id=user.id, full_name=user.full_name, avatar_url=user.avatar_url),
            body=result["body"],  # Plaintext returned to sender
            is_read=False,
            sent_at=result["sent_at"],
        )

    def mark_read(self, conv_id: int, user: User) -> dict:
        conv = self.repo.get_conversation_by_id(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.participant_1 != user.id and conv.participant_2 != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        count = self.repo.mark_messages_read(conv_id, user.id)
        return {"message": f"Marked {count} messages as read"}

    def archive_conversation(self, conv_id: int, user: User) -> dict:
        conv = self.repo.get_conversation_by_id(conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv.participant_1 != user.id and conv.participant_2 != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        self.repo.archive_conversation(conv_id, user.id)
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
