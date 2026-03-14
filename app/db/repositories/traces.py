from __future__ import annotations

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.db.models.app_event import AppEvent
from app.db.models.retrieval_trace import RetrievalTrace


class TraceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_trace(self, **kwargs) -> RetrievalTrace:
        trace = RetrievalTrace(**kwargs)
        self.db.add(trace)
        self.db.flush()
        return trace

    def get_by_trace_id(self, trace_id: str) -> RetrievalTrace | None:
        stmt = select(RetrievalTrace).where(RetrievalTrace.id == trace_id)
        return self.db.scalar(stmt)

    def delete_for_chat_session(self, chat_session_id: str) -> None:
        self.db.execute(delete(RetrievalTrace).where(RetrievalTrace.chat_session_id == chat_session_id))

    def delete_for_chat_sessions(self, chat_session_ids: list[str]) -> None:
        if not chat_session_ids:
            return
        self.db.execute(delete(RetrievalTrace).where(RetrievalTrace.chat_session_id.in_(chat_session_ids)))

    def list_recent_traces(self, *, limit: int = 50) -> list[RetrievalTrace]:
        stmt = select(RetrievalTrace).order_by(desc(RetrievalTrace.created_at)).limit(limit)
        return list(self.db.scalars(stmt))

    def create_event(self, **kwargs) -> AppEvent:
        event = AppEvent(**kwargs)
        self.db.add(event)
        self.db.flush()
        return event

    def list_recent_events(self, *, limit: int = 50) -> list[AppEvent]:
        stmt = select(AppEvent).order_by(desc(AppEvent.created_at)).limit(limit)
        return list(self.db.scalars(stmt))
