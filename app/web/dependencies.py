from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.adapters.document_conversion.libreoffice import LibreOfficeConverter
from app.adapters.document_conversion.markdown_to_pdf import MarkdownToPdfConverter
from app.adapters.document_conversion.text_to_pdf import TextToPdfConverter
from app.adapters.pdf.ocr import OcrExtractor
from app.adapters.pdf.renderer import PdfRenderer
from app.adapters.pdf.thumbnail import ThumbnailGenerator
from app.domain.schemas.auth import CurrentUserContext
from app.services import SharedServices
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.monitoring_service import MonitoringService
from app.services.retrieval_service import RetrievalService
from app.services.storage_service import StorageService


def get_shared_services(request: Request) -> SharedServices:
    return request.app.state.shared


def get_settings(request: Request):
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    session.info["app"] = request.app
    try:
        yield session
    finally:
        session.close()


def get_storage_service(shared: SharedServices = Depends(get_shared_services)) -> StorageService:
    return StorageService(shared.object_store)


def get_auth_service(db: Session = Depends(get_db), shared: SharedServices = Depends(get_shared_services)) -> AuthService:
    return AuthService(db, shared.auth_provider)


async def get_current_context(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> CurrentUserContext:
    return await auth_service.ensure_current_user(request)


def get_document_service(
    db: Session = Depends(get_db),
    shared: SharedServices = Depends(get_shared_services),
    storage: StorageService = Depends(get_storage_service),
) -> DocumentService:
    return DocumentService(
        db,
        storage,
        shared.vector_store,
        max_upload_bytes=shared.settings.max_upload_bytes,
        max_attempts=shared.settings.ingest_max_attempts,
    )


def get_retrieval_service(
    db: Session = Depends(get_db),
    shared: SharedServices = Depends(get_shared_services),
) -> RetrievalService:
    return RetrievalService(db, shared.vector_store, shared.reranker_client, shared.embedding_client, shared.settings)


def get_chat_service(
    db: Session = Depends(get_db),
    shared: SharedServices = Depends(get_shared_services),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    storage: StorageService = Depends(get_storage_service),
) -> ChatService:
    return ChatService(
        db,
        settings=shared.settings,
        retrieval_service=retrieval_service,
        llm_client=shared.llm_client,
        storage=storage,
    )


def get_monitoring_service(db: Session = Depends(get_db)) -> MonitoringService:
    return MonitoringService(db)


def get_ingestion_service(
    db: Session = Depends(get_db),
    shared: SharedServices = Depends(get_shared_services),
    storage: StorageService = Depends(get_storage_service),
) -> IngestionService:
    converters = {
        "txt": TextToPdfConverter(),
        "md": MarkdownToPdfConverter(),
        "doc": LibreOfficeConverter(),
        "docx": LibreOfficeConverter(),
        "ppt": LibreOfficeConverter(),
        "pptx": LibreOfficeConverter(),
    }
    return IngestionService(
        db,
        storage=storage,
        vector_store=shared.vector_store,
        embedding_client=shared.embedding_client,
        pdf_renderer=PdfRenderer(),
        thumbnail_generator=ThumbnailGenerator(),
        ocr_extractor=OcrExtractor(),
        converters=converters,
        ingest_max_pages=shared.settings.ingest_max_pages,
        ingest_batch_page_size=shared.settings.ingest_batch_page_size,
        ocr_enabled=shared.settings.ocr_enabled,
    )
