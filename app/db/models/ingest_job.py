from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import IngestJobStatus, IngestStep


class IngestJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ingest_jobs"
    __table_args__ = (
        Index("ix_ingest_jobs_status_created_at", "status", "created_at"),
        Index("ix_ingest_jobs_space_document", "space_id", "document_id"),
    )

    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    status: Mapped[IngestJobStatus] = mapped_column(
        Enum(IngestJobStatus, native_enum=False),
        default=IngestJobStatus.PENDING,
        nullable=False,
    )
    step: Mapped[IngestStep] = mapped_column(
        Enum(IngestStep, native_enum=False),
        default=IngestStep.QUEUED,
        nullable=False,
    )
    progress_current: Mapped[int] = mapped_column(default=0, nullable=False)
    progress_total: Mapped[int] = mapped_column(default=0, nullable=False)
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(default=3, nullable=False)
    worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(255), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document = relationship("Document", back_populates="jobs")

