from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MonitoringJobRead(BaseModel):
    id: str
    document_id: str
    document_name: str
    status: str
    step: str
    attempt_count: int
    trace_id: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None


class MonitoringChatTraceRead(BaseModel):
    id: str
    query_text: str
    trace_id: str
    top_k: int
    rerank_enabled: bool
    max_images_to_llm: int
    answer_preview: str | None = None
    latency_ms_total: int | None = None
    created_at: datetime


class AppEventRead(BaseModel):
    id: str
    event_type: str
    severity: str
    trace_id: str | None = None
    payload_json: str
    created_at: datetime

