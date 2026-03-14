from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, asc, desc, select
from sqlalchemy.orm import Session

from app.db.models.ingest_job import IngestJob
from app.domain.enums import IngestJobStatus


class JobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs) -> IngestJob:
        job = IngestJob(**kwargs)
        self.db.add(job)
        self.db.flush()
        return job

    def get_in_space(self, space_id: str, job_id: str) -> IngestJob | None:
        stmt = select(IngestJob).where(IngestJob.id == job_id, IngestJob.space_id == space_id)
        return self.db.scalar(stmt)

    def list_for_document(self, space_id: str, document_id: str) -> list[IngestJob]:
        stmt = (
            select(IngestJob)
            .where(IngestJob.space_id == space_id, IngestJob.document_id == document_id)
            .order_by(desc(IngestJob.created_at))
        )
        return list(self.db.scalars(stmt))

    def list_recent(self, *, limit: int = 50) -> list[IngestJob]:
        stmt: Select[tuple[IngestJob]] = select(IngestJob).order_by(desc(IngestJob.created_at)).limit(limit)
        return list(self.db.scalars(stmt))

    def get_next_pending(self) -> IngestJob | None:
        stmt = (
            select(IngestJob)
            .where(IngestJob.status == IngestJobStatus.PENDING)
            .order_by(asc(IngestJob.created_at))
            .limit(1)
        )
        return self.db.scalar(stmt)

    def mark_running(self, job: IngestJob, *, worker_id: str, started_at: datetime) -> IngestJob:
        job.status = IngestJobStatus.RUNNING
        job.worker_id = worker_id
        job.attempt_count += 1
        job.started_at = started_at
        self.db.flush()
        return job

