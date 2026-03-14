from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.adapters.model_clients.base import EmbeddingClient
from app.utils.images import file_to_data_url


class OpenAICompatibleEmbeddingClient(EmbeddingClient):
    def __init__(
        self,
        *,
        api_base: str,
        api_key: str,
        model: str,
        dimensions: int = 256,
        app_name: str | None = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.app_name = app_name

    def _fallback_embedding(self, image_path: str) -> list[float]:
        digest = hashlib.sha256(Path(image_path).read_bytes()).digest()
        values = [((digest[idx % len(digest)] / 255.0) * 2.0) - 1.0 for idx in range(self.dimensions)]
        return values

    def _fallback_text_embedding(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [((digest[idx % len(digest)] / 255.0) * 2.0) - 1.0 for idx in range(self.dimensions)]
        return values

    def _is_openrouter(self) -> bool:
        if not self.api_base:
            return False
        return "openrouter.ai" in urlparse(self.api_base).netloc

    def _embeddings_url(self) -> str:
        if not self.api_base:
            return ""

        if self.api_base.endswith("/embeddings"):
            return self.api_base

        if self._is_openrouter():
            if self.api_base.endswith("/api/v1") or self.api_base.endswith("/v1"):
                return f"{self.api_base}/embeddings"
            if self.api_base.endswith("/api"):
                return f"{self.api_base}/v1/embeddings"
            return f"{self.api_base}/api/v1/embeddings"

        return f"{self.api_base}/embeddings"

    def _build_input_item(self, image_path: str) -> str | dict[str, object]:
        image_url = file_to_data_url(image_path)
        if not self._is_openrouter():
            return image_url

        return {
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                }
            ]
        }

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self._is_openrouter() and self.app_name:
            headers["X-Title"] = self.app_name
        return headers

    def _request_embeddings(self, payload: dict[str, object]) -> list[list[float]]:
        headers = self._build_headers()
        with httpx.Client(timeout=60.0) as client:
            response = client.post(self._embeddings_url(), json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return [item["embedding"] for item in data["data"]]

    def embed_images(self, image_paths: list[str]) -> list[list[float]]:
        if not image_paths:
            return []
        if not self.api_base or not self.model:
            return [self._fallback_embedding(path) for path in image_paths]

        payload = {
            "model": self.model,
            "input": [self._build_input_item(path) for path in image_paths],
        }
        return self._request_embeddings(payload)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_base or not self.model:
            return [self._fallback_text_embedding(text) for text in texts]

        payload = {
            "model": self.model,
            "input": texts,
        }
        return self._request_embeddings(payload)
