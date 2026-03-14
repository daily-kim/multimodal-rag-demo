from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import orjson

from app.adapters.vector_store.base import VectorPageRecord, VectorSearchHit, VectorStore


class NanoVectorStore(VectorStore):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _space_file(self, space_id: str) -> Path:
        return self.root / f"{space_id}.jsonl"

    def _load_records(self, space_id: str) -> list[dict[str, Any]]:
        path = self._space_file(space_id)
        if not path.exists():
            return []
        return [orjson.loads(line) for line in path.read_bytes().splitlines() if line.strip()]

    def _save_records(self, space_id: str, records: list[dict[str, Any]]) -> None:
        path = self._space_file(space_id)
        payload = b"\n".join(orjson.dumps(record) for record in records)
        path.write_bytes(payload)

    def upsert_pages(self, pages: list[VectorPageRecord]) -> None:
        if not pages:
            return
        by_space: dict[str, list[VectorPageRecord]] = {}
        for page in pages:
            by_space.setdefault(page.space_id, []).append(page)

        for space_id, space_pages in by_space.items():
            existing = self._load_records(space_id)
            remaining = {record["id"]: record for record in existing}
            for page in space_pages:
                remaining[page.id] = asdict(page)
            self._save_records(space_id, list(remaining.values()))

    def search(self, space_id: str, query_vector: list[float], top_k: int, filters: dict[str, Any] | None = None) -> list[VectorSearchHit]:
        filters = filters or {}
        document_ids = set(filters.get("document_ids") or [])
        records = self._load_records(space_id)
        if document_ids:
            records = [record for record in records if record["document_id"] in document_ids]
        query_dim = len(query_vector)
        if query_dim:
            records = [record for record in records if len(record.get("embedding") or []) == query_dim]
        if not records:
            return []
        matrix = np.array([record["embedding"] for record in records], dtype=np.float32)
        query = np.array(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []
        scores = matrix @ query / ((np.linalg.norm(matrix, axis=1) * query_norm) + 1e-8)
        ranked = np.argsort(scores)[::-1][:top_k]
        hits: list[VectorSearchHit] = []
        for idx in ranked:
            record = records[int(idx)]
            hits.append(
                VectorSearchHit(
                    id=record["id"],
                    document_id=record["document_id"],
                    page_id=record["page_id"],
                    page_no=record["page_no"],
                    score=float(scores[int(idx)]),
                    image_path=record["image_path"],
                    thumbnail_path=record.get("thumbnail_path"),
                    extracted_text=record.get("extracted_text"),
                    document_filename=record["document_filename"],
                    metadata_json=record.get("metadata_json") or {},
                )
            )
        return hits

    def delete_document(self, space_id: str, document_id: str) -> None:
        records = [record for record in self._load_records(space_id) if record["document_id"] != document_id]
        self._save_records(space_id, records)

    def healthcheck(self) -> dict[str, Any]:
        files = list(self.root.glob("*.jsonl"))
        return {"backend": "nano", "root": str(self.root), "spaces": len(files)}
