from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.domain.enums import EventSeverity
from app.utils.time import utcnow


class AppEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "app_events"
    __table_args__ = (
        Index("ix_app_events_trace_created_at", "trace_id", "created_at"),
        Index("ix_app_events_space_created_at", "space_id", "created_at"),
    )

    space_id: Mapped[str | None] = mapped_column(ForeignKey("spaces.id"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[EventSeverity] = mapped_column(Enum(EventSeverity, native_enum=False), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
