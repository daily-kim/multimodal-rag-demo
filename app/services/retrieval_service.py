from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.adapters.model_clients.base import EmbeddingClient, RerankCandidate, RerankerClient
from app.adapters.vector_store.base import VectorSearchHit, VectorStore
from app.config import Settings
from app.db.models.document import Document
from app.db.models.document_page import DocumentPage
from app.db.repositories.documents import DocumentRepository
from app.domain.enums import RetrievalMode


@dataclass(slots=True)
class RetrievalHit:
    page: DocumentPage
    document: Document
    retrieval_score: float
    rerank_score: float | None = None

    def to_trace_dict(self) -> dict[str, object]:
        context_text = (self.page.extracted_text or "").strip() or None
        if context_text:
            context_text = context_text[:1200]
        return {
            "document_id": self.document.id,
            "document_name": self.document.original_filename,
            "page_id": self.page.id,
            "page_no": self.page.page_no,
            "image_path": self.page.storage_image_path,
            "thumbnail_path": self.page.storage_thumbnail_path,
            "context_text": context_text,
            "retrieval_score": self.retrieval_score,
            "rerank_score": self.rerank_score,
        }


class RetrievalService:
    def __init__(
        self,
        db: Session,
        vector_store: VectorStore,
        reranker_client: RerankerClient,
        embedding_client: EmbeddingClient,
        settings: Settings,
    ) -> None:
        self.db = db
        self.vector_store = vector_store
        self.reranker_client = reranker_client
        self.embedding_client = embedding_client
        self.settings = settings
        self.documents = DocumentRepository(db)

    def _fallback_query_vector(self, query: str, *, dimensions: int = 256) -> list[float]:
        digest = hashlib.sha256(query.encode("utf-8")).digest()
        return [((digest[idx % len(digest)] / 255.0) * 2.0) - 1.0 for idx in range(dimensions)]

    def prepare_query_vector(self, query: str, *, dimensions: int = 256) -> list[float]:
        if self.settings.embedding_api_base and self.settings.embedding_model:
            return self.embedding_client.embed_texts([query])[0]
        return self._fallback_query_vector(query, dimensions=dimensions)

    def retrieve(
        self,
        *,
        space_id: str,
        query: str,
        selected_document_ids: list[str],
        top_k: int,
    ) -> tuple[list[float], list[RetrievalHit], int]:
        started = time.perf_counter()
        if self.settings.embedding_api_base and self.settings.embedding_model:
            query_vector = self.embedding_client.embed_texts([query])[0]
            hits = self.vector_store.search(
                space_id,
                query_vector,
                top_k,
                filters={"document_ids": selected_document_ids} if selected_document_ids else {},
            )
            resolved_hits = self._resolve_vector_hits(space_id, hits)
            latency_ms = int((time.perf_counter() - started) * 1000)
            return query_vector, resolved_hits, latency_ms

        pages = self.documents.list_pages_for_space(space_id, document_ids=selected_document_ids or None)
        doc_map = {document.id: document for document in self.documents.get_many_in_space(space_id, selected_document_ids)} if selected_document_ids else {
            document.id: document for document in self.documents.list_for_space(space_id)
        }
        terms = {token for token in query.lower().split() if token}
        scored: list[RetrievalHit] = []
        for page in pages:
            text = (page.extracted_text or "").lower()
            score = float(sum(1 for token in terms if token in text))
            if score <= 0 and terms:
                continue
            document = doc_map.get(page.document_id)
            if document is None:
                continue
            scored.append(RetrievalHit(page=page, document=document, retrieval_score=score))
        scored.sort(key=lambda item: item.retrieval_score, reverse=True)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return self._fallback_query_vector(query), scored[:top_k], latency_ms

    def rerank(self, *, query: str, hits: list[RetrievalHit], top_n: int) -> tuple[list[RetrievalHit], int]:
        started = time.perf_counter()
        if not hits:
            return [], 0
        candidates = [
            RerankCandidate(
                id=hit.page.id,
                text=hit.page.extracted_text or f"{hit.document.original_filename} page {hit.page.page_no}",
                metadata={"document_id": hit.document.id, "page_no": hit.page.page_no},
            )
            for hit in hits
        ]
        reranked = self.reranker_client.rerank(query, candidates, top_n)
        score_map = {item.id: item.score for item in reranked}
        selected = [hit for hit in hits if hit.page.id in score_map]
        selected.sort(key=lambda item: score_map[item.page.id], reverse=True)
        for hit in selected:
            hit.rerank_score = score_map[hit.page.id]
        latency_ms = int((time.perf_counter() - started) * 1000)
        return selected, latency_ms

    def expand_neighbors(self, *, space_id: str, hits: list[RetrievalHit], window_n: int) -> list[RetrievalHit]:
        if not hits or window_n <= 0:
            return hits
        expanded: dict[str, RetrievalHit] = {hit.page.id: hit for hit in hits}
        grouped: dict[str, list[RetrievalHit]] = {}
        for hit in hits:
            grouped.setdefault(hit.document.id, []).append(hit)
        for document_id, doc_hits in grouped.items():
            pages = self.documents.list_pages_for_document(space_id, document_id)
            page_map = {page.page_no: page for page in pages}
            document = doc_hits[0].document
            for hit in doc_hits:
                for page_no in range(max(1, hit.page.page_no - window_n), hit.page.page_no + window_n + 1):
                    if page_no == hit.page.page_no:
                        continue
                    page = page_map.get(page_no)
                    if page is None or page.id in expanded:
                        continue
                    expanded[page.id] = RetrievalHit(
                        page=page,
                        document=document,
                        retrieval_score=hit.retrieval_score,
                        rerank_score=hit.rerank_score,
                    )
        ordered = list(expanded.values())
        ordered.sort(key=lambda item: (item.document.original_filename, item.page.page_no))
        return ordered

    def _resolve_vector_hits(self, space_id: str, hits: list[VectorSearchHit]) -> list[RetrievalHit]:
        page_ids = [hit.page_id for hit in hits]
        pages = self.documents.get_pages_by_ids(space_id, page_ids)
        page_map = {page.id: page for page in pages}
        documents = self.documents.get_many_in_space(space_id, list({page.document_id for page in pages}))
        document_map = {document.id: document for document in documents}
        resolved: list[RetrievalHit] = []
        for hit in hits:
            page = page_map.get(hit.page_id)
            if page is None:
                continue
            document = document_map.get(page.document_id)
            if document is None:
                continue
            resolved.append(RetrievalHit(page=page, document=document, retrieval_score=hit.score))
        return resolved
