from __future__ import annotations

import secrets

import httpx
from fastapi import Request
from fastapi.responses import RedirectResponse

from app.adapters.auth.base import AuthProvider


class GitHubOAuthProvider(AuthProvider):
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        access_token_url: str,
        user_api_url: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.access_token_url = access_token_url
        self.user_api_url = user_api_url

    def get_login_redirect(self, request: Request):
        state = secrets.token_urlsafe(16)
        request.session["oauth_state"] = state
        callback_url = str(request.url_for("auth_callback"))
        url = (
            f"{self.authorize_url}?client_id={self.client_id}"
            f"&redirect_uri={callback_url}&state={state}&scope=read:user user:email"
        )
        return RedirectResponse(url=url)

    async def handle_callback(self, request: Request) -> dict[str, object]:
        expected_state = request.session.get("oauth_state")
        state = request.query_params.get("state")
        if not state or state != expected_state:
            raise ValueError("Invalid OAuth state.")
        code = request.query_params.get("code")
        if not code:
            raise ValueError("Missing OAuth code.")
        callback_url = str(request.url_for("auth_callback"))
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_response = await client.post(
                self.access_token_url,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": callback_url,
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]
            user_response = await client.get(
                self.user_api_url,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            user_response.raise_for_status()
            user_payload = user_response.json()
        profile = {
            "github_id": str(user_payload["id"]),
            "username": user_payload["login"],
            "display_name": user_payload.get("name") or user_payload["login"],
            "email": user_payload.get("email"),
            "avatar_url": user_payload.get("avatar_url"),
            "is_bypass": False,
        }
        request.session["auth_user"] = profile
        return profile

    async def get_current_user(self, request: Request) -> dict[str, object] | None:
        return request.session.get("auth_user")

    async def logout(self, request: Request) -> None:
        request.session.clear()

