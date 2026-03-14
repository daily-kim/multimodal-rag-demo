from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.web.dependencies import get_current_context, get_document_service

router = APIRouter(tags=["documents-partials"])


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/partials/documents/list", response_class=HTMLResponse)
async def documents_list_partial(request: Request, current=Depends(get_current_context), document_service=Depends(get_document_service)):
    documents = document_service.list_documents(current)
    return _templates(request).TemplateResponse(
        "partials/document_list.html",
        {"request": request, "documents": documents, "current_user": current},
    )


@router.get("/partials/documents/{document_id}/row", response_class=HTMLResponse)
async def document_row_partial(
    document_id: str,
    request: Request,
    current=Depends(get_current_context),
    document_service=Depends(get_document_service),
):
    document = document_service.get_document(current, document_id)
    return _templates(request).TemplateResponse(
        "partials/document_row.html",
        {"request": request, "document": document, "current_user": current},
    )

