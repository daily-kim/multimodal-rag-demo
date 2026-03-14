from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import DocumentStatus, ExtractedTextSource


class DocumentCreate(BaseModel):
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    file_ext: str


class DocumentPageRead(BaseModel):
    id: str
    page_no: int
    width: int
    height: int
    storage_image_path: str
    storage_thumbnail_path: str | None = None
    extracted_text: str | None = None
    extracted_text_source: ExtractedTextSource
    created_at: datetime


class DocumentRead(BaseModel):
    id: str
    space_id: str
    original_filename: str
    normalized_filename: str | None = None
    file_ext: str
    mime_type: str
    status: DocumentStatus
    size_bytes: int
    sha256: str
    total_pages: int | None = None
    storage_thumbnail_path: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

