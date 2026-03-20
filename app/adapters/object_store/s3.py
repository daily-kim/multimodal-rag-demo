from __future__ import annotations

import hashlib
from pathlib import Path

import boto3

from app.adapters.object_store.base import ObjectStore, StoredObject


class S3ObjectStore(ObjectStore):
    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str,
        force_path_style: bool,
        local_cache_dir: str | Path = ".cache/s3-object-store",
    ) -> None:
        self.bucket = bucket
        self.local_cache_dir = Path(local_cache_dir).resolve()
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region or None,
            config=boto3.session.Config(s3={"addressing_style": "path" if force_path_style else "virtual"}),
        )

    def put_bytes(self, path: str, data: bytes, content_type: str | None = None) -> StoredObject:
        kwargs = {"Bucket": self.bucket, "Key": path, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        self.client.put_object(**kwargs)
        return StoredObject(path=path, content_type=content_type, size_bytes=len(data))

    def put_file(self, path: str, local_path: str) -> StoredObject:
        self.client.upload_file(local_path, self.bucket, path)
        return StoredObject(path=path, size_bytes=Path(local_path).stat().st_size)

    def get_bytes(self, path: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=path)
        return response["Body"].read()

    def delete(self, path: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=path)

    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
        except Exception:
            return False
        return True

    def presigned_url(self, path: str, expires_in: int = 3600) -> str | None:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": path},
            ExpiresIn=expires_in,
        )

    def _cache_path(self, path: str) -> Path:
        suffix = Path(path).suffix
        hashed_name = hashlib.sha256(path.encode("utf-8")).hexdigest()
        return self.local_cache_dir / f"{hashed_name}{suffix}"

    def open_local_path(self, path: str) -> str | None:
        cached = self._cache_path(path)
        if cached.exists():
            return str(cached)
        cached.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.client.download_file(self.bucket, path, str(cached))
        except Exception:
            return None
        return str(cached)
