"""
Chat module repository — optimized database operations with encrypted messages.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, or_, and_
from app.modules.chat.model import Conversation, Message
from app.core.encryption import encrypt, decrypt


class ChatRepository:
    """Handles all chat-related database queries with message encryption."""

    def __init__(self, db: Session):
        self.db = db

    def get_conversations(
        self,
        user_id: int,
        filter_type: str = "all",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict], int]:
        """Get conversation list with last message and unread count."""
        query = (
            self.db.query(Conversation)
            .options(
                joinedload(Conversation.participant_1_user),
                joinedload(Conversation.participant_2_user),
                joinedload(Conversation.book),
            )
            .filter(
                or_(
                    Conversation.participant_1 == user_id,
                    Conversation.participant_2 == user_id,
                )
            )
        )

        if filter_type == "unread":
            unread_subquery = (
                self.db.query(Message.conversation_id)
                .filter(
                    Message.sender_id != user_id,
                    Message.is_read == False,
                    Message.is_archived == False,
                )
                .distinct()
                .subquery()
            )
            query = query.filter(Conversation.id.in_(
                self.db.query(unread_subquery.c.conversation_id)
            ))
        elif filter_type == "archive":
            archive_subquery = (
                self.db.query(Message.conversation_id)
                .filter(Message.is_archived == True)
                .distinct()
                .subquery()
            )
            query = query.filter(Conversation.id.in_(
                self.db.query(archive_subquery.c.conversation_id)
            ))

        total = query.count()
        conversations = (
            query.order_by(desc(Conversation.last_message_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        conv_ids = [c.id for c in conversations]

        # Unread counts per conversation
        unread_counts = {}
        if conv_ids:
            counts = (
                self.db.query(
                    Message.conversation_id,
                    func.count(Message.id),
                )
                .filter(
                    Message.conversation_id.in_(conv_ids),
                    Message.sender_id != user_id,
                    Message.is_read == False,
                )
                .group_by(Message.conversation_id)
                .all()
            )
            unread_counts = {cid: count for cid, count in counts}

        # Last messages per conversation (decrypted)
        last_messages = {}
        if conv_ids:
            for conv_id in conv_ids:
                msg = (
                    self.db.query(Message.body_encrypted)
                    .filter(Message.conversation_id == conv_id)
                    .order_by(desc(Message.sent_at))
                    .first()
                )
                if msg:
                    last_messages[conv_id] = decrypt(msg[0])

        results = []
        for conv in conversations:
            results.append({
                "conversation": conv,
                "unread_count": unread_counts.get(conv.id, 0),
                "last_message": last_messages.get(conv.id),
            })

        return results, total

    def get_conversation_by_id(self, conv_id: int) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .options(
                joinedload(Conversation.participant_1_user),
                joinedload(Conversation.participant_2_user),
                joinedload(Conversation.book),
            )
            .filter(Conversation.id == conv_id)
            .first()
        )

    def find_existing_conversation(
        self, user_id: int, other_user_id: int, book_id: int = None
    ) -> Conversation | None:
        query = self.db.query(Conversation).filter(
            or_(
                and_(Conversation.participant_1 == user_id, Conversation.participant_2 == other_user_id),
                and_(Conversation.participant_1 == other_user_id, Conversation.participant_2 == user_id),
            )
        )
        if book_id:
            query = query.filter(Conversation.book_id == book_id)
        return query.first()

    def create_conversation(
        self, user_id: int, other_user_id: int, book_id: int = None
    ) -> Conversation:
        conv = Conversation(
            participant_1=user_id,
            participant_2=other_user_id,
            book_id=book_id,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_messages(
        self, conversation_id: int, offset: int = 0, limit: int = 50
    ) -> tuple[list[dict], int]:
        """Get messages decrypted."""
        query = (
            self.db.query(Message)
            .options(joinedload(Message.sender))
            .filter(Message.conversation_id == conversation_id)
        )
        total = query.count()
        messages = (
            query.order_by(desc(Message.sent_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        # Decrypt message bodies
        decrypted = []
        for m in messages:
            decrypted.append({
                "id": m.id,
                "sender": m.sender,
                "body": decrypt(m.body_encrypted),
                "is_read": m.is_read,
                "sent_at": m.sent_at,
            })

        return decrypted, total

    def send_message(self, conversation_id: int, sender_id: int, body: str) -> dict:
        """Encrypt and send a message, update conversation's last_message_at."""
        now = datetime.now(timezone.utc)
        encrypted_body = encrypt(body)

        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            body_encrypted=encrypted_body,
            sent_at=now,
        )
        self.db.add(msg)

        self.db.query(Conversation).filter(Conversation.id == conversation_id).update(
            {"last_message_at": now}
        )
        self.db.commit()
        self.db.refresh(msg)

        return {
            "id": msg.id,
            "body": body,  # Return plaintext to the sender
            "sent_at": msg.sent_at,
        }

    def mark_messages_read(self, conversation_id: int, user_id: int) -> int:
        count = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.is_read == False,
            )
            .update({"is_read": True})
        )
        self.db.commit()
        return count

    def archive_conversation(self, conversation_id: int, user_id: int) -> int:
        count = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .update({"is_archived": True})
        )
        self.db.commit()
        return count

    def get_total_unread_count(self, user_id: int) -> int:
        return (
            self.db.query(func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(
                or_(
                    Conversation.participant_1 == user_id,
                    Conversation.participant_2 == user_id,
                ),
                Message.sender_id != user_id,
                Message.is_read == False,
                Message.is_archived == False,
            )
            .scalar() or 0
        )
