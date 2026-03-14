from __future__ import annotations

from pathlib import Path

from app.adapters.document_conversion.base import ConversionResult, DocumentConverter
from app.adapters.document_conversion.text_to_pdf import render_text_pdf


class MarkdownToPdfConverter(DocumentConverter):
    def convert(self, source_path: str | Path, output_path: str | Path) -> ConversionResult:
        markdown_text = Path(source_path).read_text(encoding="utf-8", errors="ignore")
        return render_text_pdf(markdown_text, output_path, title=Path(source_path).name)

