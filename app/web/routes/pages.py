from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.domain.schemas.chat import RetrievalConfig
from app.web.dependencies import (
    get_chat_service,
    get_current_context,
    get_document_service,
    get_monitoring_service,
)

router = APIRouter(tags=["pages"])


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.app.state.settings.auth_bypass:
        return RedirectResponse(url="/auth/login", status_code=303)
    return _templates(request).TemplateResponse("login.html", {"request": request, "page_title": "Login"})


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current=Depends(get_current_context),
    document_service=Depends(get_document_service),
    monitoring_service=Depends(get_monitoring_service),
):
    documents = document_service.list_documents(current)
    jobs = monitoring_service.recent_jobs(limit=10)
    chats = monitoring_service.recent_chats(limit=10)
    return _templates(request).TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "page_title": "Dashboard",
            "current_user": current,
            "documents": documents,
            "jobs": jobs,
            "chats": chats,
        },
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request, current=Depends(get_current_context), document_service=Depends(get_document_service)):
    documents = document_service.list_documents(current)
    return _templates(request).TemplateResponse(
        "documents.html",
        {
            "request": request,
            "page_title": "Documents",
            "current_user": current,
            "documents": documents,
        },
    )


@router.get("/documents/{document_id}", response_class=HTMLResponse)
async def document_detail_page(
    document_id: str,
    request: Request,
    current=Depends(get_current_context),
    document_service=Depends(get_document_service),
):
    document = document_service.get_document(current, document_id)
    return _templates(request).TemplateResponse(
        "document_detail.html",
        {
            "request": request,
            "page_title": "Document Detail",
            "current_user": current,
            "document": document,
        },
    )


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    current=Depends(get_current_context),
    document_service=Depends(get_document_service),
    chat_service=Depends(get_chat_service),
    session_id: str | None = None,
    new: bool = False,
):
    documents = document_service.list_documents(current)
    chat_sessions = chat_service.list_recent_sessions(current, limit=20)
    session = chat_service.resolve_session(current, session_id=session_id, force_new=new)
    if new:
        chat_sessions = [session, *[item for item in chat_sessions if item.id != session.id]]
    elif all(item.id != session.id for item in chat_sessions):
        chat_sessions = [session, *chat_sessions]
    messages = chat_service.list_messages(current, session.id)
    retrieval_defaults = RetrievalConfig()
    for message in reversed(messages):
        if not getattr(message, "retrieval_config_json", None):
            continue
        retrieval_defaults = RetrievalConfig.model_validate_json(message.retrieval_config_json)
        break
    selected_document_ids = set(json.loads(session.selected_document_ids_json or "[]"))
    latest_trace_id = next((message.trace_id for message in reversed(messages) if message.trace_id), None)
    latest_response = SimpleNamespace(trace_id=latest_trace_id) if latest_trace_id else None
    return _templates(request).TemplateResponse(
        "chat.html",
        {
            "request": request,
            "page_title": "Chat",
            "current_user": current,
            "documents": documents,
            "chat_sessions": chat_sessions,
            "chat_session": session,
            "messages": messages,
            "selected_document_ids": selected_document_ids,
            "retrieval_defaults": retrieval_defaults,
            "latest_response": latest_response,
        },
    )


@router.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request, current=Depends(get_current_context), monitoring_service=Depends(get_monitoring_service)):
    return _templates(request).TemplateResponse(
        "monitoring.html",
        {
            "request": request,
            "page_title": "Monitoring",
            "current_user": current,
            "jobs": monitoring_service.recent_jobs(limit=25),
            "chat_traces": monitoring_service.recent_chats(limit=25),
            "events": monitoring_service.recent_events(limit=25),
        },
    )
