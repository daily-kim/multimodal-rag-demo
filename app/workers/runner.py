from __future__ import annotations

import time
from uuid import uuid4

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_engine, get_session_factory
from app.logging import configure_logging, get_logger
from app.main import create_shared_services
from app.services.ingestion_service import IngestionService
from app.services.storage_service import StorageService
from app.workers.ingest_worker import IngestWorker


logger = get_logger(__name__)


def build_ingestion_service(*, settings, shared, db):
    storage = StorageService(shared.object_store)
    from app.adapters.document_conversion.libreoffice import LibreOfficeConverter
    from app.adapters.document_conversion.markdown_to_pdf import MarkdownToPdfConverter
    from app.adapters.document_conversion.text_to_pdf import TextToPdfConverter
    from app.adapters.pdf.ocr import OcrExtractor
    from app.adapters.pdf.renderer import PdfRenderer
    from app.adapters.pdf.thumbnail import ThumbnailGenerator

    converters = {
        "txt": TextToPdfConverter(),
        "md": MarkdownToPdfConverter(),
        "doc": LibreOfficeConverter(),
        "docx": LibreOfficeConverter(),
        "ppt": LibreOfficeConverter(),
        "pptx": LibreOfficeConverter(),
    }
    service = IngestionService(
        db,
        storage=storage,
        vector_store=shared.vector_store,
        embedding_client=shared.embedding_client,
        pdf_renderer=PdfRenderer(),
        thumbnail_generator=ThumbnailGenerator(),
        ocr_extractor=OcrExtractor(),
        converters=converters,
        ingest_max_pages=settings.ingest_max_pages,
        ingest_batch_page_size=settings.ingest_batch_page_size,
        ocr_enabled=settings.ocr_enabled,
    )
    return service


def run_worker_loop() -> None:
    settings = get_settings()
    configure_logging(settings)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = get_session_factory(settings)
    shared = create_shared_services(settings)
    worker_id = f"worker-{uuid4().hex[:8]}"
    logger.info("worker started", extra={"poll_seconds": settings.ingest_worker_poll_seconds})
    while True:
        db = session_factory()
        try:
            ingestion_service = build_ingestion_service(settings=settings, shared=shared, db=db)
            worker = IngestWorker(worker_id=worker_id, ingestion_service=ingestion_service)
            processed = worker.run_once()
        except Exception:
            db.rollback()
            logger.exception("worker loop failed", extra={"worker_id": worker_id})
            processed = False
        finally:
            db.close()
        if not processed:
            time.sleep(settings.ingest_worker_poll_seconds)
