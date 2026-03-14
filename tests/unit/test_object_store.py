from __future__ import annotations

from app.adapters.object_store.filesystem import FilesystemObjectStore


def test_filesystem_object_store_roundtrip(tmp_path) -> None:
    store = FilesystemObjectStore(tmp_path)
    store.put_bytes("spaces/a/documents/b/original/test.txt", b"hello", content_type="text/plain")
    assert store.exists("spaces/a/documents/b/original/test.txt")
    assert store.get_bytes("spaces/a/documents/b/original/test.txt") == b"hello"
    assert store.open_local_path("spaces/a/documents/b/original/test.txt") is not None
    store.delete("spaces/a/documents/b/original/test.txt")
    assert not store.exists("spaces/a/documents/b/original/test.txt")

