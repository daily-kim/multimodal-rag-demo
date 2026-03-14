from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.domain.enums import ExtractedTextSource
from app.utils.time import utcnow


class DocumentPage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_no", name="uq_document_pages_document_page_no"),
        Index("ix_document_pages_space_document", "space_id", "document_id"),
    )

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), nullable=False)
    page_no: Mapped[int] = mapped_column(nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    storage_image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text_source: Mapped[ExtractedTextSource] = mapped_column(
        Enum(ExtractedTextSource, native_enum=False),
        default=ExtractedTextSource.NONE,
        nullable=False,
    )
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prev_page_id: Mapped[str | None] = mapped_column(ForeignKey("document_pages.id"), nullable=True)
    next_page_id: Mapped[str | None] = mapped_column(ForeignKey("document_pages.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    document = relationship("Document", back_populates="pages")
