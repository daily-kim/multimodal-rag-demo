from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VectorPageRecord:
    id: str
    space_id: str
    document_id: str
    page_id: str
    page_no: int
    embedding: list[float]
    image_path: str
    thumbnail_path: str | None
    extracted_text: str | None
    document_filename: str
    created_at: str
    embedding_model: str
    embedding_version: str
    metadata_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VectorSearchHit:
    id: str
    document_id: str
    page_id: str
    page_no: int
    score: float
    image_path: str
    thumbnail_path: str | None
    extracted_text: str | None
    document_filename: str
    metadata_json: dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    @abstractmethod
    def upsert_pages(self, pages: list[VectorPageRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, space_id: str, query_vector: list[float], top_k: int, filters: dict[str, Any] | None = None) -> list[VectorSearchHit]:
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, space_id: str, document_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> dict[str, Any]:
        raise NotImplementedError

