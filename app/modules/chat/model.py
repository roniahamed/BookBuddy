"""
Conversation and Message SQLAlchemy models.
Messages are stored with encrypted body for user privacy.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Conversation(Base):
    """Chat thread between two users. Triggered from the CHAT button on Book Details page."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    participant_1 = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    participant_2 = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="SET NULL"), nullable=True,
                     comment="Book the conversation is about (optional context)")
    last_message_at = Column(DateTime(timezone=True), nullable=True,
                             comment="Denormalized for sorting the conversation list")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    participant_1_user = relationship("User", foreign_keys=[participant_1])
    participant_2_user = relationship("User", foreign_keys=[participant_2])
    book = relationship("Book")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                           order_by="Message.sent_at.desc()")

    __table_args__ = (
        Index("idx_conversation_participants_book", "participant_1", "participant_2", "book_id"),
        Index("idx_conversation_participant_1", "participant_1"),
        Index("idx_conversation_participant_2", "participant_2"),
    )


class Message(Base):
    """
    Individual messages within a conversation.
    body_encrypted stores Fernet-encrypted message content for end-to-end privacy.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body_encrypted = Column(Text, nullable=False, comment="Fernet-encrypted message content")
    is_read = Column(Boolean, default=False, comment="Used for Unread filter")
    is_archived = Column(Boolean, default=False, comment="Supports the Archive tab")
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User")

    __table_args__ = (
        Index("idx_messages_conversation_sent", "conversation_id", "sent_at"),
        Index("idx_messages_sender", "sender_id"),
    )
