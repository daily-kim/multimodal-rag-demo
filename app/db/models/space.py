from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Space(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "spaces"
    __table_args__ = (
        Index("ix_spaces_user_default", "user_id", "is_default"),
        Index("ix_spaces_user_slug", "user_id", "slug", unique=True),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="spaces")

