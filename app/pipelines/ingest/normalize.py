from __future__ import annotations

import shutil
from pathlib import Path

from app.adapters.document_conversion.base import DocumentConverter
from app.adapters.pdf.renderer import PdfRenderer
from app.db.models.document import Document
from app.domain.exceptions import ValidationError
from app.services.storage_service import StorageService


def normalize_to_pdf(
    *,
    document: Document,
    storage: StorageService,
    temp_dir: Path,
    converters: dict[str, DocumentConverter],
    renderer: PdfRenderer,
) -> Path:
    source_local = storage.local_path(document.storage_original_path)
    if source_local is None:
        source_bytes = storage.object_store.get_bytes(document.storage_original_path)
        source_local = str(temp_dir / document.original_filename)
        Path(source_local).write_bytes(source_bytes)
    source_path = Path(source_local)
    output_path = temp_dir / "normalized" / "document.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if document.file_ext == "pdf":
        try:
            renderer.page_count(source_path)
        except Exception as exc:
            raise ValidationError(f"Uploaded PDF is invalid: {exc}") from exc
        shutil.copy2(source_path, output_path)
        return output_path
    converter = converters.get(document.file_ext)
    if converter is None:
        raise ValidationError(f"No converter configured for .{document.file_ext}")
    converter.convert(source_path, output_path)
    return output_path

