from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import orjson
from sqlalchemy.orm import Session

from app.adapters.document_conversion.base import DocumentConverter
from app.adapters.model_clients.base import EmbeddingClient
from app.adapters.pdf.ocr import OcrExtractor
from app.adapters.pdf.renderer import PdfRenderer
from app.adapters.pdf.thumbnail import ThumbnailGenerator
from app.adapters.vector_store.base import VectorPageRecord, VectorStore
from app.db.models.document import Document
from app.db.models.ingest_job import IngestJob
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.traces import TraceRepository
from app.domain.enums import (
    DocumentStatus,
    EventSeverity,
    ExtractedTextSource,
    IngestJobStatus,
    IngestStep,
)
from app.domain.exceptions import AppError, ExternalServiceError, ValidationError
from app.pipelines.ingest.embed_pages import batch_embeddings
from app.pipelines.ingest.extract_text import resolve_text_for_page
from app.pipelines.ingest.normalize import normalize_to_pdf
from app.pipelines.ingest.render_pdf import render_document_pdf
from app.pipelines.ingest.upsert_vectors import build_vector_records
from app.services.storage_service import StorageService
from app.logging import get_logger
from app.utils.hashes import sha256_file
from app.utils.time import utcnow


logger = get_logger(__name__)


class IngestionService:
    def __init__(
        self,
        db: Session,
        *,
        storage: StorageService,
        vector_store: VectorStore,
        embedding_client: EmbeddingClient,
        pdf_renderer: PdfRenderer,
        thumbnail_generator: ThumbnailGenerator,
        ocr_extractor: OcrExtractor,
        converters: dict[str, DocumentConverter],
        ingest_max_pages: int,
        ingest_batch_page_size: int,
        ocr_enabled: bool,
    ) -> None:
        self.db = db
        self.storage = storage
        self.vector_store = vector_store
        self.embedding_client = embedding_client
        self.pdf_renderer = pdf_renderer
        self.thumbnail_generator = thumbnail_generator
        self.ocr_extractor = ocr_extractor
        self.converters = converters
        self.ingest_max_pages = ingest_max_pages
        self.ingest_batch_page_size = ingest_batch_page_size
        self.ocr_enabled = ocr_enabled
        self.documents = DocumentRepository(db)
        self.jobs = JobRepository(db)
        self.traces = TraceRepository(db)

    def process_pending_job(self, worker_id: str) -> bool:
        job = self.jobs.get_next_pending()
        if job is None:
            return False
        self.process_job(job.id, worker_id)
        return True

    def process_job(self, job_id: str, worker_id: str) -> IngestJob:
        job = self.db.get(IngestJob, job_id)
        if job is None:
            raise ValidationError("Job not found.")
        document = self.db.get(Document, job.document_id)
        if document is None:
            raise ValidationError("Document not found.")

        temp_dir = Path(tempfile.mkdtemp(prefix=f"ingest-{job.id}-"))
        try:
            self.jobs.mark_running(job, worker_id=worker_id, started_at=utcnow())
            document.status = DocumentStatus.PROCESSING
            self.db.commit()

            self._set_step(job, IngestStep.NORMALIZE, current=1)
            local_pdf = normalize_to_pdf(
                document=document,
                storage=self.storage,
                temp_dir=temp_dir,
                converters=self.converters,
                renderer=self.pdf_renderer,
            )
            document.storage_pdf_path = self.storage.normalized_pdf_path(document.space_id, document.id)
            self.storage.object_store.put_file(document.storage_pdf_path, str(local_pdf))
            document.normalized_filename = "document.pdf"
            self.db.commit()

            self._set_step(job, IngestStep.RENDER, current=2)
            self.documents.delete_pages_for_document(document.id)
            render_output = render_document_pdf(
                document=document,
                pdf_path=local_pdf,
                temp_dir=temp_dir,
                renderer=self.pdf_renderer,
                thumbnail_generator=self.thumbnail_generator,
                storage=self.storage,
                max_pages=self.ingest_max_pages,
            )
            if len(render_output.pages) > self.ingest_max_pages:
                raise ValidationError("Document exceeds maximum page limit.")
            db_pages = []
            for rendered in render_output.pages:
                image_store_path = self.storage.page_image_path(document.space_id, document.id, rendered.page_no)
                thumb_store_path = self.storage.page_thumbnail_path(document.space_id, document.id, rendered.page_no)
                self.storage.object_store.put_file(image_store_path, str(rendered.image_path))
                if rendered.thumbnail_path:
                    self.storage.object_store.put_file(thumb_store_path, str(rendered.thumbnail_path))
                db_page = self.documents.add_page(
                    document_id=document.id,
                    space_id=document.space_id,
                    page_no=rendered.page_no,
                    width=rendered.width,
                    height=rendered.height,
                    storage_image_path=image_store_path,
                    storage_thumbnail_path=thumb_store_path if rendered.thumbnail_path else None,
                    extracted_text=None,
                    extracted_text_source=ExtractedTextSource.NONE,
                    checksum=sha256_file(rendered.image_path),
                    prev_page_id=None,
                    next_page_id=None,
                )
                db_pages.append((db_page, rendered))
            for index, (page, _) in enumerate(db_pages):
                if index > 0:
                    page.prev_page_id = db_pages[index - 1][0].id
                if index + 1 < len(db_pages):
                    page.next_page_id = db_pages[index + 1][0].id
            document.total_pages = len(db_pages)
            document.storage_thumbnail_path = db_pages[0][0].storage_thumbnail_path if db_pages else None
            self.db.commit()

            self._set_step(job, IngestStep.EXTRACT, current=3)
            extracted_manifest: dict[str, str | None] = {}
            for page, rendered in db_pages:
                text, source = resolve_text_for_page(
                    native_text=rendered.extracted_text,
                    ocr_enabled=self.ocr_enabled,
                    ocr_extractor=self.ocr_extractor,
                    image_path=rendered.image_path,
                )
                page.extracted_text = text
                page.extracted_text_source = source
                extracted_manifest[str(page.page_no)] = text
            self.db.commit()

            self._set_step(job, IngestStep.EMBED, current=4)
            embeddings = batch_embeddings(
                embedding_client=self.embedding_client,
                image_paths=[str(rendered.image_path) for _, rendered in db_pages],
                batch_size=self.ingest_batch_page_size,
            )

            self._set_step(job, IngestStep.UPSERT, current=5)
            vector_records = build_vector_records(document=document, pages=db_pages, embeddings=embeddings)
            self.vector_store.upsert_pages(vector_records)

            self._set_step(job, IngestStep.FINALIZE, current=6)
            manifest_path = self.storage.derived_path(document.space_id, document.id, "manifest.json")
            extracted_path = self.storage.derived_path(document.space_id, document.id, "extracted_text.json")
            self.storage.object_store.put_bytes(
                manifest_path,
                orjson.dumps(
                    {
                        "document_id": document.id,
                        "space_id": document.space_id,
                        "total_pages": document.total_pages,
                        "status": document.status,
                        "pages": [
                            {
                                "page_id": page.id,
                                "page_no": page.page_no,
                                "image_path": page.storage_image_path,
                                "thumbnail_path": page.storage_thumbnail_path,
                            }
                            for page, _ in db_pages
                        ],
                    }
                ),
                content_type="application/json",
            )
            self.storage.object_store.put_bytes(extracted_path, orjson.dumps(extracted_manifest), content_type="application/json")
            document.status = DocumentStatus.READY
            document.error_code = None
            document.error_message = None
            job.status = IngestJobStatus.SUCCEEDED
            job.finished_at = utcnow()
            self.traces.create_event(
                space_id=document.space_id,
                user_id=document.created_by_user_id,
                event_type="ingest.succeeded",
                severity=EventSeverity.INFO,
                trace_id=job.trace_id,
                payload_json=json.dumps({"document_id": document.id, "job_id": job.id}),
            )
            self.db.commit()
            return job
        except AppError as exc:
            self._fail_job(job, document, code=exc.code, message=exc.message)
            raise
        except Exception as exc:
            self._fail_job(job, document, code="ingest_failed", message=str(exc))
            raise
        finally:
            try:
                self._set_cleanup_step(job)
            except Exception:
                self.db.rollback()
                logger.exception("failed to persist cleanup step", extra={"job_id": job.id, "document_id": document.id})
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _set_step(self, job: IngestJob, step: IngestStep, *, current: int) -> None:
        job.step = step
        job.progress_current = current
        self.db.commit()

    def _set_cleanup_step(self, job: IngestJob) -> None:
        job.step = IngestStep.CLEANUP
        self.db.commit()

    def _fail_job(self, job: IngestJob, document: Document, *, code: str, message: str) -> None:
        document.status = DocumentStatus.FAILED
        document.error_code = code
        document.error_message = message
        job.status = IngestJobStatus.FAILED
        job.error_code = code
        job.error_message = message
        job.finished_at = utcnow()
        self.traces.create_event(
            space_id=document.space_id,
            user_id=document.created_by_user_id,
            event_type="ingest.failed",
            severity=EventSeverity.ERROR,
            trace_id=job.trace_id,
            payload_json=json.dumps({"document_id": document.id, "job_id": job.id, "error_code": code}),
        )
        self.db.commit()
