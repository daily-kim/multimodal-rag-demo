from __future__ import annotations

from app.services.storage_service import StorageService


class _FakeObjectStore:
    def __init__(self, *, presigned: str | None, local_path: str | None) -> None:
        self._presigned = presigned
        self._local_path = local_path

    def presigned_url(self, path: str, expires_in: int = 3600) -> str | None:
        return self._presigned

    def open_local_path(self, path: str) -> str | None:
        return self._local_path


def test_llm_image_input_prefers_presigned_url() -> None:
    storage = StorageService(_FakeObjectStore(presigned="https://signed.example/image.png", local_path="/tmp/image.png"))
    assert storage.llm_image_input("spaces/a/documents/b/pages/0001.png") == "https://signed.example/image.png"


def test_llm_image_input_falls_back_to_local_path() -> None:
    storage = StorageService(_FakeObjectStore(presigned=None, local_path="/tmp/image.png"))
    assert storage.llm_image_input("spaces/a/documents/b/pages/0001.png") == "/tmp/image.png"
