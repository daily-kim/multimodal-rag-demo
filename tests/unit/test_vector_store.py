from __future__ import annotations

from app.adapters.vector_store.base import VectorPageRecord
from app.adapters.vector_store.nano import NanoVectorStore


def test_nano_vector_store_upsert_search_delete(tmp_path) -> None:
    store = NanoVectorStore(tmp_path)
    store.upsert_pages(
        [
            VectorPageRecord(
                id="page-1",
                space_id="space-1",
                document_id="doc-1",
                page_id="page-1",
                page_no=1,
                embedding=[1.0, 0.0],
                image_path="a.png",
                thumbnail_path=None,
                extracted_text="hello",
                document_filename="doc.pdf",
                created_at="2026-01-01T00:00:00Z",
                embedding_model="fake",
                embedding_version="v1",
                metadata_json={},
            ),
            VectorPageRecord(
                id="page-2",
                space_id="space-1",
                document_id="doc-2",
                page_id="page-2",
                page_no=1,
                embedding=[0.0, 1.0],
                image_path="b.png",
                thumbnail_path=None,
                extracted_text="world",
                document_filename="doc2.pdf",
                created_at="2026-01-01T00:00:00Z",
                embedding_model="fake",
                embedding_version="v1",
                metadata_json={},
            ),
        ]
    )
    hits = store.search("space-1", [0.9, 0.1], top_k=1)
    assert hits[0].page_id == "page-1"
    store.delete_document("space-1", "doc-1")
    hits_after_delete = store.search("space-1", [1.0, 0.0], top_k=10)
    assert all(hit.document_id != "doc-1" for hit in hits_after_delete)


def test_nano_vector_store_ignores_dimension_mismatches(tmp_path) -> None:
    store = NanoVectorStore(tmp_path)
    store.upsert_pages(
        [
            VectorPageRecord(
                id="page-1",
                space_id="space-1",
                document_id="doc-1",
                page_id="page-1",
                page_no=1,
                embedding=[1.0, 0.0],
                image_path="a.png",
                thumbnail_path=None,
                extracted_text="hello",
                document_filename="doc.pdf",
                created_at="2026-01-01T00:00:00Z",
                embedding_model="fake",
                embedding_version="v1",
                metadata_json={},
            ),
            VectorPageRecord(
                id="page-2",
                space_id="space-1",
                document_id="doc-2",
                page_id="page-2",
                page_no=1,
                embedding=[0.0, 1.0, 0.0],
                image_path="b.png",
                thumbnail_path=None,
                extracted_text="world",
                document_filename="doc2.pdf",
                created_at="2026-01-01T00:00:00Z",
                embedding_model="fake",
                embedding_version="v1",
                metadata_json={},
            ),
        ]
    )

    hits = store.search("space-1", [0.9, 0.1], top_k=5)

    assert len(hits) == 1
    assert hits[0].page_id == "page-1"
