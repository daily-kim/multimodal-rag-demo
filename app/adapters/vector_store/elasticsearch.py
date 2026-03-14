from __future__ import annotations

from typing import Any

from elasticsearch import Elasticsearch

from app.adapters.vector_store.base import VectorPageRecord, VectorSearchHit, VectorStore


class ElasticsearchVectorStore(VectorStore):
    def __init__(self, host: str, username: str, password: str, index_prefix: str) -> None:
        self.client = Elasticsearch(hosts=[host], basic_auth=(username, password) if username else None)
        self.index_prefix = index_prefix

    def upsert_pages(self, pages: list[VectorPageRecord]) -> None:
        raise NotImplementedError("Elasticsearch upsert will be completed in phase 3.")

    def search(self, space_id: str, query_vector: list[float], top_k: int, filters: dict[str, Any] | None = None) -> list[VectorSearchHit]:
        raise NotImplementedError("Elasticsearch search will be completed in phase 3.")

    def delete_document(self, space_id: str, document_id: str) -> None:
        raise NotImplementedError("Elasticsearch delete will be completed in phase 3.")

    def healthcheck(self) -> dict[str, Any]:
        return {"backend": "elasticsearch", "ok": self.client.ping()}

