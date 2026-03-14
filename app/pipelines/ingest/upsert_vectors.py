from __future__ import annotations

from app.adapters.vector_store.base import VectorPageRecord
from app.db.models.document import Document
from app.pipelines.ingest.render_pdf import StoredRenderedPage


def build_vector_records(
    *,
    document: Document,
    pages: list[tuple[object, StoredRenderedPage]],
    embeddings: list[list[float]],
) -> list[VectorPageRecord]:
    records: list[VectorPageRecord] = []
    for (db_page, _rendered), embedding in zip(pages, embeddings, strict=False):
        records.append(
            VectorPageRecord(
                id=db_page.id,
                space_id=document.space_id,
                document_id=document.id,
                page_id=db_page.id,
                page_no=db_page.page_no,
                embedding=embedding,
                image_path=db_page.storage_image_path,
                thumbnail_path=db_page.storage_thumbnail_path,
                extracted_text=db_page.extracted_text,
                document_filename=document.original_filename,
                created_at=document.created_at.isoformat(),
                embedding_model="fallback" if not document.normalized_filename else "configured",
                embedding_version="v1",
                metadata_json={"checksum": db_page.checksum},
            )
        )
    return records

