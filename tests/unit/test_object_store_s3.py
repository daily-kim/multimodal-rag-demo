from __future__ import annotations

from pathlib import Path

from app.adapters.object_store.s3 import S3ObjectStore


class _FakeS3Client:
    def __init__(self) -> None:
        self.download_calls: list[tuple[str, str, str]] = []

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        self.download_calls.append((bucket, key, filename))
        Path(filename).write_bytes(b"image-bytes")


class _FailingS3Client:
    def download_file(self, bucket: str, key: str, filename: str) -> None:
        raise RuntimeError("missing")


def test_s3_object_store_open_local_path_downloads_and_caches(monkeypatch, tmp_path) -> None:
    fake_client = _FakeS3Client()
    monkeypatch.setattr("app.adapters.object_store.s3.boto3.client", lambda *args, **kwargs: fake_client)

    store = S3ObjectStore(
        bucket="unit-bucket",
        endpoint_url="",
        access_key="key",
        secret_key="secret",
        region="",
        force_path_style=True,
        local_cache_dir=tmp_path,
    )

    first = store.open_local_path("spaces/s1/documents/d1/pages/0001.png")
    second = store.open_local_path("spaces/s1/documents/d1/pages/0001.png")

    assert first is not None
    assert second == first
    assert Path(first).read_bytes() == b"image-bytes"
    assert len(fake_client.download_calls) == 1


def test_s3_object_store_open_local_path_returns_none_when_download_fails(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.adapters.object_store.s3.boto3.client", lambda *args, **kwargs: _FailingS3Client())

    store = S3ObjectStore(
        bucket="unit-bucket",
        endpoint_url="",
        access_key="key",
        secret_key="secret",
        region="",
        force_path_style=True,
        local_cache_dir=tmp_path,
    )

    assert store.open_local_path("spaces/s1/documents/d1/pages/missing.png") is None
