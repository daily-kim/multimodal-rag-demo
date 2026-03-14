from __future__ import annotations

import httpx

from app.adapters.model_clients.base import RerankCandidate, RerankHit, RerankerClient


class OpenAICompatibleRerankerClient(RerankerClient):
    def __init__(self, *, api_base: str, api_key: str, model: str) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model

    def rerank(self, query: str, candidates: list[RerankCandidate], top_n: int) -> list[RerankHit]:
        if not candidates:
            return []
        if not self.api_base or not self.model:
            fallback = [RerankHit(id=item.id, score=float(len(item.text)), metadata=item.metadata) for item in candidates]
            return sorted(fallback, key=lambda item: item.score, reverse=True)[:top_n]

        payload = {
            "model": self.model,
            "query": query,
            "documents": [{"id": item.id, "text": item.text, "metadata": item.metadata} for item in candidates],
            "top_n": top_n,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{self.api_base}/rerank", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return [RerankHit(id=item["id"], score=item["score"], metadata=item.get("metadata", {})) for item in data["data"]]

