from __future__ import annotations

import shutil
from pathlib import Path

from app.adapters.object_store.base import ObjectStore, StoredObject
from app.utils.hashes import sha256_file


class FilesystemObjectStore(ObjectStore):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if self.root not in target.parents and target != self.root:
            raise ValueError("Path escapes storage root.")
        return target

    def put_bytes(self, path: str, data: bytes, content_type: str | None = None) -> StoredObject:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return StoredObject(path=path, content_type=content_type, size_bytes=len(data), etag=sha256_file(target))

    def put_file(self, path: str, local_path: str) -> StoredObject:
        source = Path(local_path)
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return StoredObject(path=path, size_bytes=target.stat().st_size, etag=sha256_file(target))

    def get_bytes(self, path: str) -> bytes:
        return self._resolve(path).read_bytes()

    def delete(self, path: str) -> None:
        target = self._resolve(path)
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink(missing_ok=True)

    def delete_prefix(self, path: str) -> None:
        self.delete(path)

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def presigned_url(self, path: str, expires_in: int = 3600) -> str | None:
        return None

    def open_local_path(self, path: str) -> str | None:
        target = self._resolve(path)
        return str(target) if target.exists() else None

