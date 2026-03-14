from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, delete, desc, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.document import Document
from app.db.models.document_page import DocumentPage
from app.domain.enums import DocumentStatus


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs) -> Document:
        document = Document(**kwargs)
        self.db.add(document)
        self.db.flush()
        return document

    def list_for_space(self, space_id: str, *, include_deleted: bool = False) -> list[Document]:
        stmt: Select[tuple[Document]] = (
            select(Document)
            .where(Document.space_id == space_id)
            .options(selectinload(Document.pages), selectinload(Document.jobs))
            .order_by(desc(Document.created_at))
        )
        if not include_deleted:
            stmt = stmt.where(Document.deleted_at.is_(None), Document.status != DocumentStatus.DELETED)
        return list(self.db.scalars(stmt))

    def find_active_duplicate(self, space_id: str, sha256: str) -> Document | None:
        stmt = select(Document).where(
            Document.space_id == space_id,
            Document.sha256 == sha256,
            Document.deleted_at.is_(None),
        )
        return self.db.scalar(stmt)

    def get_in_space(self, space_id: str, document_id: str) -> Document | None:
        stmt = (
            select(Document)
            .where(Document.id == document_id, Document.space_id == space_id)
            .options(selectinload(Document.pages), selectinload(Document.jobs))
        )
        return self.db.scalar(stmt)

    def get_many_in_space(self, space_id: str, document_ids: list[str]) -> list[Document]:
        if not document_ids:
            return []
        stmt = select(Document).where(Document.space_id == space_id, Document.id.in_(document_ids), Document.deleted_at.is_(None))
        return list(self.db.scalars(stmt))

    def list_pages_for_document(self, space_id: str, document_id: str) -> list[DocumentPage]:
        stmt = (
            select(DocumentPage)
            .where(DocumentPage.space_id == space_id, DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_no.asc())
        )
        return list(self.db.scalars(stmt))

    def list_pages_for_space(self, space_id: str, *, document_ids: list[str] | None = None) -> list[DocumentPage]:
        stmt = select(DocumentPage).where(DocumentPage.space_id == space_id)
        if document_ids:
            stmt = stmt.where(DocumentPage.document_id.in_(document_ids))
        stmt = stmt.order_by(DocumentPage.document_id.asc(), DocumentPage.page_no.asc())
        return list(self.db.scalars(stmt))

    def get_page(self, space_id: str, page_id: str) -> DocumentPage | None:
        stmt = select(DocumentPage).where(DocumentPage.space_id == space_id, DocumentPage.id == page_id)
        return self.db.scalar(stmt)

    def get_pages_by_ids(self, space_id: str, page_ids: list[str]) -> list[DocumentPage]:
        if not page_ids:
            return []
        stmt = select(DocumentPage).where(DocumentPage.space_id == space_id, DocumentPage.id.in_(page_ids))
        pages = list(self.db.scalars(stmt))
        page_order = {page_id: idx for idx, page_id in enumerate(page_ids)}
        pages.sort(key=lambda page: page_order.get(page.id, 0))
        return pages

    def add_page(self, **kwargs) -> DocumentPage:
        page = DocumentPage(**kwargs)
        self.db.add(page)
        self.db.flush()
        return page

    def delete_pages_for_document(self, document_id: str) -> None:
        self.db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        self.db.flush()

    def soft_delete(self, document: Document, *, deleted_at: datetime) -> Document:
        document.deleted_at = deleted_at
        document.status = DocumentStatus.DELETED
        self.db.flush()
        return document
