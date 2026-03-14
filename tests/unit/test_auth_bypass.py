from __future__ import annotations

import asyncio

from app.adapters.auth.bypass_auth import BypassAuthProvider


class DummyRequest:
    def __init__(self) -> None:
        self.session: dict[str, object] = {}


def test_bypass_provider_sets_session_user() -> None:
    provider = BypassAuthProvider()
    request = DummyRequest()
    provider.get_login_redirect(request)  # type: ignore[arg-type]
    profile = asyncio.run(provider.get_current_user(request))  # type: ignore[arg-type]
    assert profile is not None
    assert profile["username"] == "dev-user"
    assert profile["is_bypass"] is True
