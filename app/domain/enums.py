from __future__ import annotations

from enum import StrEnum


class DocumentSourceType(StrEnum):
    UPLOAD = "upload"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class ExtractedTextSource(StrEnum):
    NONE = "none"
    NATIVE = "native"
    OCR = "ocr"
    HYBRID = "hybrid"


class IngestJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class IngestStep(StrEnum):
    QUEUED = "queued"
    NORMALIZE = "normalize"
    RENDER = "render"
    EXTRACT = "extract"
    EMBED = "embed"
    UPSERT = "upsert"
    FINALIZE = "finalize"
    CLEANUP = "cleanup"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class RetrievalMode(StrEnum):
    PAGES_ONLY = "pages_only"
    WITH_NEIGHBORS = "with_neighbors"


class EventSeverity(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

