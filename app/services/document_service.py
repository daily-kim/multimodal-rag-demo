from __future__ import annotations

import json
import mimetypes
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.adapters.vector_store.base import VectorStore
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.traces import TraceRepository
from app.domain.enums import DocumentSourceType, DocumentStatus, EventSeverity, IngestJobStatus, IngestStep
from app.domain.exceptions import NotFoundError, ValidationError
from app.domain.schemas.auth import CurrentUserContext
from app.services.storage_service import StorageService
from app.utils.files import file_extension, sanitize_filename
from app.utils.ids import generate_id
from app.utils.time import utcnow


class DocumentService:
    def __init__(
        self,
        db: Session,
        storage: StorageService,
        vector_store: VectorStore,
        *,
        max_upload_bytes: int,
        max_attempts: int,
    ) -> None:
        self.db = db
        self.storage = storage
        self.vector_store = vector_store
        self.max_upload_bytes = max_upload_bytes
        self.max_attempts = max_attempts
        self.documents = DocumentRepository(db)
        self.jobs = JobRepository(db)
        self.traces = TraceRepository(db)

    async def upload_document(self, context: CurrentUserContext, file: UploadFile) -> tuple[object, object]:
        filename = sanitize_filename(file.filename or "upload.bin")
        extension = file_extension(filename)
        if extension not in ("pdf", "txt", "md", "doc", "docx", "ppt", "pptx"):
            raise ValidationError("Unsupported file type.")
        payload = await file.read()
        if not payload:
            raise ValidationError("Uploaded file is empty.")
        if len(payload) > self.max_upload_bytes:
            raise ValidationError("Uploaded file exceeds maximum allowed size.")

        sha256 = __import__("hashlib").sha256(payload).hexdigest()
        duplicate = self.documents.find_active_duplicate(context.space_id, sha256)
        document_id = generate_id()
        trace_id = generate_id()
        original_path = self.storage.original_path(context.space_id, document_id, filename)
        self.storage.object_store.put_bytes(original_path, payload, content_type=file.content_type or None)

        document = self.documents.create(
            id=document_id,
            space_id=context.space_id,
            original_filename=filename,
            normalized_filename=None,
            file_ext=extension,
            mime_type=file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            source_type=DocumentSourceType.UPLOAD,
            status=DocumentStatus.UPLOADED,
            size_bytes=len(payload),
            sha256=sha256,
            total_pages=None,
            storage_original_path=original_path,
            storage_pdf_path=None,
            storage_thumbnail_path=None,
            error_code=None,
            error_message="Duplicate checksum detected." if duplicate else None,
            created_by_user_id=context.user_id,
        )
        job = self.jobs.create(
            space_id=context.space_id,
            document_id=document.id,
            status=IngestJobStatus.PENDING,
            step=IngestStep.QUEUED,
            progress_current=0,
            progress_total=7,
            attempt_count=0,
            max_attempts=self.max_attempts,
            worker_id=None,
            trace_id=trace_id,
        )
        self.traces.create_event(
            space_id=context.space_id,
            user_id=context.user_id,
            event_type="document.uploaded",
            severity=EventSeverity.INFO,
            trace_id=trace_id,
            payload_json=json.dumps({"document_id": document.id, "filename": filename, "duplicate": bool(duplicate)}),
        )
        self.db.commit()
        self.db.refresh(document)
        self.db.refresh(job)
        return document, job

    def list_documents(self, context: CurrentUserContext) -> list[object]:
        return self.documents.list_for_space(context.space_id)

    def get_document(self, context: CurrentUserContext, document_id: str):
        document = self.documents.get_in_space(context.space_id, document_id)
        if not document:
            raise NotFoundError("Document not found.")
        return document

    def delete_document(self, context: CurrentUserContext, document_id: str) -> None:
        document = self.documents.get_in_space(context.space_id, document_id)
        if not document:
            raise NotFoundError("Document not found.")
        trace_id = generate_id()
        document.status = DocumentStatus.DELETING
        self.db.flush()
        errors: list[str] = []
        try:
            self.vector_store.delete_document(context.space_id, document.id)
        except Exception as exc:
            errors.append(f"vector_delete:{exc}")
        try:
            self.storage.delete_document_prefix(context.space_id, document.id)
        except Exception as exc:
            errors.append(f"storage_delete:{exc}")
        document.deleted_at = utcnow()
        document.status = DocumentStatus.DELETED
        self.traces.create_event(
            space_id=context.space_id,
            user_id=context.user_id,
            event_type="document.deleted",
            severity=EventSeverity.WARNING if errors else EventSeverity.INFO,
            trace_id=trace_id,
            payload_json=json.dumps({"document_id": document.id, "errors": errors}),
        )
        self.db.commit()
