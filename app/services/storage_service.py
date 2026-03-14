from __future__ import annotations

from pathlib import Path

from app.adapters.object_store.base import ObjectStore


class StorageService:
    def __init__(self, object_store: ObjectStore) -> None:
        self.object_store = object_store

    @staticmethod
    def document_prefix(space_id: str, document_id: str) -> str:
        return f"spaces/{space_id}/documents/{document_id}"

    def original_path(self, space_id: str, document_id: str, filename: str) -> str:
        return f"{self.document_prefix(space_id, document_id)}/original/{filename}"

    def normalized_pdf_path(self, space_id: str, document_id: str) -> str:
        return f"{self.document_prefix(space_id, document_id)}/normalized/document.pdf"

    def page_image_path(self, space_id: str, document_id: str, page_no: int) -> str:
        return f"{self.document_prefix(space_id, document_id)}/pages/{page_no:04d}.png"

    def page_thumbnail_path(self, space_id: str, document_id: str, page_no: int) -> str:
        return f"{self.document_prefix(space_id, document_id)}/thumbnails/{page_no:04d}.jpg"

    def derived_path(self, space_id: str, document_id: str, filename: str) -> str:
        return f"{self.document_prefix(space_id, document_id)}/derived/{filename}"

    def local_path(self, path: str) -> str | None:
        return self.object_store.open_local_path(path)

    def delete_document_prefix(self, space_id: str, document_id: str) -> None:
        prefix = self.document_prefix(space_id, document_id)
        delete_prefix = getattr(self.object_store, "delete_prefix", None)
        if callable(delete_prefix):
            delete_prefix(prefix)
        else:
            self.object_store.delete(prefix)

    def ensure_local_parent(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

