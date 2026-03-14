from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.domain.enums import RetrievalMode
from app.utils.time import utcnow


class RetrievalTrace(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "retrieval_traces"
    __table_args__ = (
        Index("ix_retrieval_traces_space_created_at", "space_id", "created_at"),
        Index("ix_retrieval_traces_trace_created_at", "created_at", "chat_session_id"),
    )

    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), nullable=False)
    chat_session_id: Mapped[str | None] = mapped_column(ForeignKey("chat_sessions.id"), nullable=True)
    user_message_id: Mapped[str | None] = mapped_column(ForeignKey("chat_messages.id"), nullable=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    selected_document_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    retrieval_mode: Mapped[RetrievalMode] = mapped_column(
        Enum(RetrievalMode, native_enum=False),
        nullable=False,
        default=RetrievalMode.WITH_NEIGHBORS,
    )
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    rerank_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rerank_top_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_images_to_llm: Mapped[int] = mapped_column(Integer, nullable=False)
    neighbor_window_n: Mapped[int] = mapped_column(Integer, nullable=False)
    retrieved_items_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    reranked_items_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    final_context_items_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    llm_request_summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    answer_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms_retrieve: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms_rerank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms_generate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
