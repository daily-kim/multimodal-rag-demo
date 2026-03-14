from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(slots=True)
class RenderedPage:
    page_no: int
    width: int
    height: int
    image_path: Path
    extracted_text: str | None = None


class PdfRenderer:
    def render(self, pdf_path: str | Path, output_dir: str | Path, *, zoom: float = 2.0) -> list[RenderedPage]:
        doc = fitz.open(pdf_path)
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        pages: list[RenderedPage] = []
        matrix = fitz.Matrix(zoom, zoom)
        for index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image_path = target_dir / f"{index:04d}.png"
            pix.save(image_path)
            pages.append(
                RenderedPage(
                    page_no=index,
                    width=pix.width,
                    height=pix.height,
                    image_path=image_path,
                    extracted_text=page.get_text("text") or None,
                )
            )
        return pages

    def page_count(self, pdf_path: str | Path) -> int:
        with fitz.open(pdf_path) as doc:
            return doc.page_count

