from __future__ import annotations

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.chat_message import ChatMessage
from app.db.models.chat_session import ChatSession


class ChatRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, *, space_id: str, user_id: str, title: str | None = None, selected_document_ids_json: str = "[]") -> ChatSession:
        session = ChatSession(
            space_id=space_id,
            user_id=user_id,
            title=title,
            selected_document_ids_json=selected_document_ids_json,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def get_session_in_space(self, space_id: str, session_id: str) -> ChatSession | None:
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.space_id == space_id)
            .options(selectinload(ChatSession.messages))
        )
        return self.db.scalar(stmt)

    def get_latest_session_for_user(self, *, space_id: str, user_id: str) -> ChatSession | None:
        stmt = (
            select(ChatSession)
            .where(ChatSession.space_id == space_id, ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.updated_at), desc(ChatSession.created_at))
            .limit(1)
            .options(selectinload(ChatSession.messages))
        )
        return self.db.scalar(stmt)

    def delete_session(self, session: ChatSession) -> None:
        self.db.delete(session)

    def delete_messages_for_session(self, session_id: str) -> None:
        self.db.execute(delete(ChatMessage).where(ChatMessage.chat_session_id == session_id))

    def add_message(self, **kwargs) -> ChatMessage:
        message = ChatMessage(**kwargs)
        self.db.add(message)
        self.db.flush()
        return message

    def get_message_in_session(self, session_id: str, message_id: str) -> ChatMessage | None:
        stmt = select(ChatMessage).where(ChatMessage.chat_session_id == session_id, ChatMessage.id == message_id)
        return self.db.scalar(stmt)

    def list_messages(self, session_id: str) -> list[ChatMessage]:
        stmt = select(ChatMessage).where(ChatMessage.chat_session_id == session_id).order_by(ChatMessage.created_at.asc())
        return list(self.db.scalars(stmt))

    def list_recent_sessions_for_user(self, *, space_id: str, user_id: str, limit: int = 50) -> list[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.space_id == space_id, ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.updated_at), desc(ChatSession.created_at))
            .limit(limit)
        )
        return list(self.db.scalars(stmt))
