from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserProfile(BaseModel):
    id: str
    username: str
    display_name: str
    email: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class CurrentUserContext(BaseModel):
    user_id: str
    space_id: str
    username: str
    display_name: str
    is_bypass: bool = False
