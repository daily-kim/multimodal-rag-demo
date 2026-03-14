from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_github_id(self, github_id: str) -> User | None:
        stmt = select(User).where(User.github_id == github_id)
        return self.db.scalar(stmt)

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self.db.scalar(stmt)

    def create(
        self,
        *,
        username: str,
        display_name: str,
        github_id: str | None = None,
        email: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        user = User(
            github_id=github_id,
            username=username,
            display_name=display_name,
            email=email,
            avatar_url=avatar_url,
        )
        self.db.add(user)
        self.db.flush()
        return user

