from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import DocumentSourceType, DocumentStatus


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_space_status", "space_id", "status"),
        Index("ix_documents_space_created_at", "space_id", "created_at"),
        Index("ix_documents_space_sha256", "space_id", "sha256"),
    )

    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_ext: Mapped[str] = mapped_column(String(32), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[DocumentSourceType] = mapped_column(
        Enum(DocumentSourceType, native_enum=False),
        default=DocumentSourceType.UPLOAD,
        nullable=False,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    total_pages: Mapped[int | None] = mapped_column(nullable=True)
    storage_original_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_pdf_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan", lazy="selectin")
    jobs = relationship("IngestJob", back_populates="document", cascade="all, delete-orphan", lazy="selectin")

