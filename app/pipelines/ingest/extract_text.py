from __future__ import annotations

from pathlib import Path

from app.adapters.pdf.ocr import OcrExtractor
from app.domain.enums import ExtractedTextSource


def resolve_text_for_page(
    *,
    native_text: str | None,
    ocr_enabled: bool,
    ocr_extractor: OcrExtractor,
    image_path: str | Path,
) -> tuple[str | None, ExtractedTextSource]:
    normalized_native = (native_text or "").strip() or None
    if normalized_native:
        return normalized_native, ExtractedTextSource.NATIVE
    if ocr_enabled:
        ocr_text = (ocr_extractor.extract(image_path) or "").strip() or None
        if ocr_text:
            return ocr_text, ExtractedTextSource.OCR
    return None, ExtractedTextSource.NONE

