from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from fastapi import Request


class AuthProvider(ABC):
    @abstractmethod
    def get_login_redirect(self, request: Request) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def handle_callback(self, request: Request) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_current_user(self, request: Request) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def logout(self, request: Request) -> None:
        raise NotImplementedError

