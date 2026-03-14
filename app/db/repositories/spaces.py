from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.space import Space


class SpaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, space_id: str) -> Space | None:
        return self.db.get(Space, space_id)

    def get_default_for_user(self, user_id: str) -> Space | None:
        stmt = select(Space).where(Space.user_id == user_id, Space.is_default.is_(True))
        return self.db.scalar(stmt)

    def list_for_user(self, user_id: str) -> list[Space]:
        stmt = select(Space).where(Space.user_id == user_id).order_by(Space.created_at.asc())
        return list(self.db.scalars(stmt))

    def create(self, *, user_id: str, name: str, slug: str, is_default: bool = False) -> Space:
        space = Space(user_id=user_id, name=name, slug=slug, is_default=is_default)
        self.db.add(space)
        self.db.flush()
        return space

