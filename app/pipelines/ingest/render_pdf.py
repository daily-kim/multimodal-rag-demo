from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.adapters.pdf.renderer import PdfRenderer, RenderedPage
from app.adapters.pdf.thumbnail import ThumbnailGenerator
from app.db.models.document import Document
from app.domain.exceptions import ValidationError
from app.services.storage_service import StorageService


@dataclass(slots=True)
class StoredRenderedPage:
    page_no: int
    width: int
    height: int
    image_path: Path
    thumbnail_path: Path | None
    extracted_text: str | None


@dataclass(slots=True)
class RenderOutput:
    pages: list[StoredRenderedPage]


def render_document_pdf(
    *,
    document: Document,
    pdf_path: Path,
    temp_dir: Path,
    renderer: PdfRenderer,
    thumbnail_generator: ThumbnailGenerator,
    storage: StorageService,
    max_pages: int,
) -> RenderOutput:
    render_dir = temp_dir / "pages"
    thumb_dir = temp_dir / "thumbs"
    rendered_pages = renderer.render(pdf_path, render_dir)
    if len(rendered_pages) > max_pages:
        raise ValidationError("Document exceeds maximum page limit.")
    pages: list[StoredRenderedPage] = []
    for rendered in rendered_pages:
        thumbnail_path = thumb_dir / f"{rendered.page_no:04d}.jpg"
        thumbnail_generator.create(rendered.image_path, thumbnail_path)
        pages.append(
            StoredRenderedPage(
                page_no=rendered.page_no,
                width=rendered.width,
                height=rendered.height,
                image_path=rendered.image_path,
                thumbnail_path=thumbnail_path,
                extracted_text=rendered.extracted_text,
            )
        )
    return RenderOutput(pages=pages)

