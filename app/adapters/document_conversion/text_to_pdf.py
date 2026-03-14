from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.adapters.document_conversion.base import ConversionResult, DocumentConverter


def render_text_pdf(text: str, output_path: str | Path, *, title: str = "Document") -> ConversionResult:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(target), pagesize=A4)
    width, height = A4
    y = height - 50
    pdf.setTitle(title)
    pdf.setFont("Helvetica", 10)
    for line in text.splitlines() or [""]:
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - 50
        pdf.drawString(50, y, line[:110])
        y -= 14
    pdf.save()
    return ConversionResult(output_path=target)


class TextToPdfConverter(DocumentConverter):
    def convert(self, source_path: str | Path, output_path: str | Path) -> ConversionResult:
        text = Path(source_path).read_text(encoding="utf-8", errors="ignore")
        return render_text_pdf(text, output_path, title=Path(source_path).name)

