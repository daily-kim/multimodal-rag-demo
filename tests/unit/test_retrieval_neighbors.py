from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.vector_store.nano import NanoVectorStore
from app.config import Settings
from app.db.base import Base
from app.db.models.document import Document
from app.db.models.document_page import DocumentPage
from app.db.models.space import Space
from app.db.models.user import User
from app.domain.enums import DocumentSourceType, DocumentStatus, ExtractedTextSource
from app.services.retrieval_service import RetrievalHit, RetrievalService
from tests.fakes import FakeEmbeddingClient, FakeRerankerClient


def test_neighbor_expansion_respects_document_boundaries(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    user = User(username="u", display_name="U")
    session.add(user)
    session.flush()
    space = Space(user_id=user.id, name="S", slug="s", is_default=True)
    session.add(space)
    session.flush()
    document = Document(
        space_id=space.id,
        original_filename="test.pdf",
        normalized_filename="document.pdf",
        file_ext="pdf",
        mime_type="application/pdf",
        source_type=DocumentSourceType.UPLOAD,
        status=DocumentStatus.READY,
        size_bytes=1,
        sha256="a" * 64,
        total_pages=3,
        storage_original_path="orig",
        storage_pdf_path="pdf",
        storage_thumbnail_path=None,
        created_by_user_id=user.id,
    )
    session.add(document)
    session.flush()
    pages = []
    for page_no in (1, 2, 3):
        page = DocumentPage(
            document_id=document.id,
            space_id=space.id,
            page_no=page_no,
            width=10,
            height=10,
            storage_image_path=f"page-{page_no}.png",
            storage_thumbnail_path=None,
            extracted_text=f"page {page_no}",
            extracted_text_source=ExtractedTextSource.NATIVE,
            checksum=str(page_no),
        )
        session.add(page)
        session.flush()
        pages.append(page)
    session.commit()

    settings = Settings(
        sqlite_path=str(tmp_path / "app.db"),
        filesystem_storage_root=str(tmp_path / "data"),
        nano_vector_path=str(tmp_path / "vectors"),
    )
    service = RetrievalService(session, NanoVectorStore(tmp_path / "vectors"), FakeRerankerClient(), FakeEmbeddingClient(), settings)
    hit = RetrievalHit(page=pages[1], document=document, retrieval_score=1.0)
    expanded = service.expand_neighbors(space_id=space.id, hits=[hit], window_n=1)
    assert [item.page.page_no for item in expanded] == [1, 2, 3]
