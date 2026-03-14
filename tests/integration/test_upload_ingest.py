from __future__ import annotations

import asyncio
from io import BytesIO

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.document_conversion.markdown_to_pdf import MarkdownToPdfConverter
from app.adapters.document_conversion.text_to_pdf import TextToPdfConverter
from app.adapters.object_store.filesystem import FilesystemObjectStore
from app.adapters.pdf.ocr import OcrExtractor
from app.adapters.pdf.renderer import PdfRenderer
from app.adapters.pdf.thumbnail import ThumbnailGenerator
from app.adapters.vector_store.nano import NanoVectorStore
from app.config import Settings
from app.db.base import Base
from app.db.repositories.chats import ChatRepository
from app.db.repositories.spaces import SpaceRepository
from app.db.repositories.users import UserRepository
from app.domain.schemas.auth import CurrentUserContext
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.storage_service import StorageService
from tests.fakes import FakeEmbeddingClient


def test_upload_and_ingest_txt_document(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    user = UserRepository(session).create(username="dev-user", display_name="Developer")
    space = SpaceRepository(session).create(user_id=user.id, name="Default", slug="default", is_default=True)
    session.commit()

    object_store = FilesystemObjectStore(tmp_path / "data")
    vector_store = NanoVectorStore(tmp_path / "vectors")
    storage = StorageService(object_store)
    context = CurrentUserContext(user_id=user.id, space_id=space.id, username=user.username, display_name=user.display_name)

    document_service = DocumentService(session, storage, vector_store, max_upload_bytes=1024 * 1024, max_attempts=3)
    upload = UploadFile(filename="demo.txt", file=BytesIO(b"hello world\nthis is a test document"))
    document, job = asyncio.run(document_service.upload_document(context, upload))

    ingestion_service = IngestionService(
        session,
        storage=storage,
        vector_store=vector_store,
        embedding_client=FakeEmbeddingClient(),
        pdf_renderer=PdfRenderer(),
        thumbnail_generator=ThumbnailGenerator(),
        ocr_extractor=OcrExtractor(),
        converters={"txt": TextToPdfConverter(), "md": MarkdownToPdfConverter()},
        ingest_max_pages=20,
        ingest_batch_page_size=4,
        ocr_enabled=False,
    )
    ingestion_service.process_job(job.id, "worker-test")
    session.refresh(document)
    assert document.status.value == "ready"
    assert document.total_pages >= 1
    assert object_store.exists(document.storage_pdf_path)
    assert vector_store.healthcheck()["spaces"] == 1

    other_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    try:
        chat_session = ChatRepository(other_session).create_session(space_id=space.id, user_id=user.id)
        other_session.commit()
        assert chat_session.id
    finally:
        other_session.close()
