from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.repositories.chats import ChatRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.traces import TraceRepository


class MonitoringService:
    def __init__(self, db: Session) -> None:
        self.jobs = JobRepository(db)
        self.chats = ChatRepository(db)
        self.traces = TraceRepository(db)

    def recent_jobs(self, *, limit: int = 50):
        return self.jobs.list_recent(limit=limit)

    def recent_chats(self, *, limit: int = 50):
        return self.traces.list_recent_traces(limit=limit)

    def recent_events(self, *, limit: int = 50):
        return self.traces.list_recent_events(limit=limit)

