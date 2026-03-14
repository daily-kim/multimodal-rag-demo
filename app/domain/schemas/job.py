from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import IngestJobStatus, IngestStep


class IngestJobRead(BaseModel):
    id: str
    document_id: str
    status: IngestJobStatus
    step: IngestStep
    progress_current: int
    progress_total: int
    attempt_count: int
    max_attempts: int
    worker_id: str | None = None
    trace_id: str
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

