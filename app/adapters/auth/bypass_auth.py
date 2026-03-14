from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse

from app.adapters.auth.base import AuthProvider


class BypassAuthProvider(AuthProvider):
    def get_login_redirect(self, request: Request):
        request.session["auth_user"] = {
            "github_id": None,
            "username": "dev-user",
            "display_name": "Developer User",
            "email": "dev@example.com",
            "avatar_url": None,
            "is_bypass": True,
        }
        return RedirectResponse(url="/")

    async def handle_callback(self, request: Request) -> dict[str, object]:
        return request.session.get("auth_user", {})

    async def get_current_user(self, request: Request) -> dict[str, object] | None:
        return request.session.get("auth_user")

    async def logout(self, request: Request) -> None:
        request.session.clear()

