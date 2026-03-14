from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class StoredObject:
    path: str
    content_type: str | None = None
    size_bytes: int | None = None
    etag: str | None = None


class ObjectStore(ABC):
    @abstractmethod
    def put_bytes(self, path: str, data: bytes, content_type: str | None = None) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    def put_file(self, path: str, local_path: str) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    def get_bytes(self, path: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def delete(self, path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def presigned_url(self, path: str, expires_in: int = 3600) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def open_local_path(self, path: str) -> str | None:
        raise NotImplementedError

