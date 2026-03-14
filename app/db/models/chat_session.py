from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_space_user", "space_id", "user_id"),
    )

    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    selected_document_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    messages = relationship("ChatMessage", back_populates="chat_session", cascade="all, delete-orphan", lazy="selectin")

