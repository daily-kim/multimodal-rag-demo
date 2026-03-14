from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from app.db.repositories.documents import DocumentRepository
from app.db.repositories.jobs import JobRepository
from app.domain.exceptions import AppError, NotFoundError
from app.web.dependencies import get_current_context, get_db, get_document_service

router = APIRouter(prefix="/api", tags=["api-documents"])


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile,
    current=Depends(get_current_context),
    document_service=Depends(get_document_service),
):
    document, job = await document_service.upload_document(current, file)
    if request.headers.get("HX-Request") == "true":
        documents = document_service.list_documents(current)
        return request.app.state.templates.TemplateResponse(
            "partials/document_list.html",
            {"request": request, "documents": documents, "current_user": current},
        )
    return {"document_id": document.id, "job_id": job.id}


@router.get("/documents")
async def list_documents(current=Depends(get_current_context), document_service=Depends(get_document_service)):
    documents = document_service.list_documents(current)
    return [
        {
            "id": document.id,
            "original_filename": document.original_filename,
            "status": document.status,
            "total_pages": document.total_pages,
            "created_at": document.created_at.isoformat(),
        }
        for document in documents
    ]


@router.get("/documents/{document_id}")
async def get_document(document_id: str, current=Depends(get_current_context), document_service=Depends(get_document_service)):
    document = document_service.get_document(current, document_id)
    return {
        "id": document.id,
        "status": document.status,
        "original_filename": document.original_filename,
        "pages": [
            {
                "id": page.id,
                "page_no": page.page_no,
                "thumbnail_path": page.storage_thumbnail_path,
                "image_path": page.storage_image_path,
            }
            for page in document.pages
        ],
    }


@router.delete("/documents/{document_id}")
async def delete_document(request: Request, document_id: str, current=Depends(get_current_context), document_service=Depends(get_document_service)):
    document_service.delete_document(current, document_id)
    if request.headers.get("HX-Request") == "true":
        documents = document_service.list_documents(current)
        return request.app.state.templates.TemplateResponse(
            "partials/document_list.html",
            {"request": request, "documents": documents, "current_user": current},
        )
    return JSONResponse({"ok": True})


@router.get("/documents/{document_id}/jobs")
async def get_document_jobs(document_id: str, current=Depends(get_current_context), db=Depends(get_db)):
    jobs = JobRepository(db).list_for_document(current.space_id, document_id)
    return [
        {
            "id": job.id,
            "status": job.status,
            "step": job.step,
            "trace_id": job.trace_id,
            "attempt_count": job.attempt_count,
            "error_message": job.error_message,
        }
        for job in jobs
    ]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, current=Depends(get_current_context), db=Depends(get_db)):
    job = JobRepository(db).get_in_space(current.space_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "id": job.id,
        "status": job.status,
        "step": job.step,
        "progress_current": job.progress_current,
        "progress_total": job.progress_total,
        "trace_id": job.trace_id,
    }


@router.get("/documents/{document_id}/pages/{page_id}/thumbnail")
async def page_thumbnail(request: Request, document_id: str, page_id: str, current=Depends(get_current_context), db=Depends(get_db)):
    page = DocumentRepository(db).get_page(current.space_id, page_id)
    if page is None or page.document_id != document_id:
        raise HTTPException(status_code=404, detail="Page not found.")
    return _serve_asset(request, page.storage_thumbnail_path, content_type="image/jpeg")


@router.get("/documents/{document_id}/pages/{page_id}/image")
async def page_image(request: Request, document_id: str, page_id: str, current=Depends(get_current_context), db=Depends(get_db)):
    page = DocumentRepository(db).get_page(current.space_id, page_id)
    if page is None or page.document_id != document_id:
        raise HTTPException(status_code=404, detail="Page not found.")
    return _serve_asset(request, page.storage_image_path, content_type="image/png")


def _serve_asset(request: Request, path: str | None, *, content_type: str):
    if path is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    local_path = request.app.state.shared.object_store.open_local_path(path)
    if local_path:
        return FileResponse(local_path)
    data = request.app.state.shared.object_store.get_bytes(path)
    return Response(content=data, media_type=content_type)
