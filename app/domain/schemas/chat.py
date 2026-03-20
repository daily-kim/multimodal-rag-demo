from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import ChatRole, RetrievalMode


class RetrievalConfig(BaseModel):
    top_k: int = Field(default=12, ge=1, le=100)
    rerank_enabled: bool = True
    rerank_top_n: int = Field(default=6, ge=1, le=100)
    max_images_to_llm: int = Field(default=6, ge=1, le=32)
    retrieval_mode: RetrievalMode = RetrievalMode.WITH_NEIGHBORS
    neighbor_window_n: int = Field(default=1, ge=0, le=10)

    @field_validator("rerank_top_n")
    @classmethod
    def _validate_rerank_top_n(cls, value: int) -> int:
        return max(1, value)

    @classmethod
    def from_settings(cls, settings: Any) -> "RetrievalConfig":
        return cls(
            top_k=settings.rag_default_top_k,
            rerank_enabled=settings.rag_default_rerank_enabled,
            rerank_top_n=settings.rag_default_rerank_top_n,
            max_images_to_llm=settings.rag_default_max_images_to_llm,
            retrieval_mode=settings.rag_default_retrieval_mode,
            neighbor_window_n=settings.rag_default_neighbor_window_n,
        )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    selected_document_ids: list[str] = Field(default_factory=list)
    retrieval_config: RetrievalConfig


class ChatMessageRead(BaseModel):
    id: str
    role: ChatRole
    content: str
    model_name: str | None = None
    trace_id: str | None = None
    created_at: datetime


class EvidenceItem(BaseModel):
    document_id: str
    document_name: str
    page_id: str
    page_no: int
    image_path: str
    thumbnail_path: str | None = None
    context_text: str | None = None
    retrieval_score: float | None = None
    rerank_score: float | None = None


class ChatResponse(BaseModel):
    session_id: str
    trace_id: str
    answer: str
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
