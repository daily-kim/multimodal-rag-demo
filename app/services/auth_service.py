from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.adapters.auth.base import AuthProvider
from app.db.repositories.spaces import SpaceRepository
from app.db.repositories.traces import TraceRepository
from app.db.repositories.users import UserRepository
from app.domain.enums import EventSeverity
from app.domain.exceptions import AuthenticationError
from app.domain.schemas.auth import CurrentUserContext
from app.utils.files import slugify


class AuthService:
    def __init__(self, db: Session, provider: AuthProvider) -> None:
        self.db = db
        self.provider = provider
        self.users = UserRepository(db)
        self.spaces = SpaceRepository(db)
        self.traces = TraceRepository(db)

    async def ensure_current_user(self, request: Request) -> CurrentUserContext:
        just_logged_in = False
        profile = await self.provider.get_current_user(request)
        if not profile:
            if request.app.state.settings.auth_bypass:
                self.provider.get_login_redirect(request)
                profile = await self.provider.get_current_user(request)
                just_logged_in = True
        if not profile:
            raise AuthenticationError()
        return self._sync_user_and_space(profile, record_login_event=just_logged_in)

    async def handle_callback(self, request: Request) -> CurrentUserContext:
        profile = await self.provider.handle_callback(request)
        return self._sync_user_and_space(profile, record_login_event=True)

    async def logout(self, request: Request) -> None:
        context = await self.provider.get_current_user(request)
        await self.provider.logout(request)
        if context:
            self.traces.create_event(
                user_id=None,
                space_id=None,
                event_type="auth.logout",
                severity=EventSeverity.INFO,
                trace_id=None,
                payload_json="{}",
            )
            self.db.commit()

    def _sync_user_and_space(self, profile: dict[str, object], *, record_login_event: bool = False) -> CurrentUserContext:
        github_id = str(profile["github_id"]) if profile.get("github_id") else None
        username = str(profile["username"])
        display_name = str(profile["display_name"])
        email = str(profile["email"]) if profile.get("email") else None
        avatar_url = str(profile["avatar_url"]) if profile.get("avatar_url") else None
        is_bypass = bool(profile.get("is_bypass", False))

        user = self.users.get_by_github_id(github_id) if github_id else self.users.get_by_username(username)
        if user is None:
            user = self.users.create(
                github_id=github_id,
                username=username,
                display_name=display_name,
                email=email,
                avatar_url=avatar_url,
            )
        else:
            user.username = username
            user.display_name = display_name
            user.email = email
            user.avatar_url = avatar_url

        space = self.spaces.get_default_for_user(user.id)
        if space is None:
            slug = slugify(f"{username}-default")
            space = self.spaces.create(user_id=user.id, name=f"{display_name} Space", slug=slug, is_default=True)

        if record_login_event:
            self.traces.create_event(
                space_id=space.id,
                user_id=user.id,
                event_type="auth.login",
                severity=EventSeverity.INFO,
                trace_id=None,
                payload_json='{"provider":"github"}' if not is_bypass else '{"provider":"bypass"}',
            )
        self.db.commit()
        return CurrentUserContext(
            user_id=user.id,
            space_id=space.id,
            username=user.username,
            display_name=user.display_name,
            is_bypass=is_bypass,
        )
