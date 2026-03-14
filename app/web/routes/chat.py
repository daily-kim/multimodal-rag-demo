from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.db.repositories.chats import ChatRepository
from app.db.repositories.traces import TraceRepository
from app.domain.schemas.chat import RetrievalConfig
from app.web.dependencies import get_current_context, get_db

router = APIRouter(tags=["chat-partials"])


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/partials/chat/{session_id}/messages", response_class=HTMLResponse)
async def chat_messages_partial(
    session_id: str,
    request: Request,
    trace_id: str | None = None,
    current=Depends(get_current_context),
    db=Depends(get_db),
):
    chats = ChatRepository(db)
    traces = TraceRepository(db)
    session = chats.get_session_in_space(current.space_id, session_id)
    messages = chats.list_messages(session_id) if session else []
    retrieval_defaults = RetrievalConfig()
    for message in reversed(messages):
        if not message.retrieval_config_json:
            continue
        retrieval_defaults = RetrievalConfig.model_validate_json(message.retrieval_config_json)
        break
    trace = traces.get_by_trace_id(trace_id) if trace_id else None
    latest_response = None
    if trace and trace.space_id == current.space_id:
        latest_response = SimpleNamespace(
            trace_id=trace.id,
            evidence_items=json.loads(trace.final_context_items_json),
        )
    return _templates(request).TemplateResponse(
        "partials/chat_panel.html",
        {
            "request": request,
            "current_user": current,
            "chat_session": session,
            "messages": messages,
            "latest_response": latest_response,
            "retrieval_defaults": retrieval_defaults,
        },
    )


@router.get("/partials/chat/{session_id}/evidence/{trace_id}", response_class=HTMLResponse)
async def chat_evidence_partial(
    session_id: str,
    trace_id: str,
    request: Request,
    current=Depends(get_current_context),
    db=Depends(get_db),
):
    traces = TraceRepository(db)
    trace = traces.get_by_trace_id(trace_id)
    if trace is None or trace.space_id != current.space_id:
        evidence_items = []
    else:
        evidence_items = json.loads(trace.final_context_items_json)
    return _templates(request).TemplateResponse(
        "partials/evidence_panel.html",
        {
            "request": request,
            "current_user": current,
            "trace": trace,
            "evidence_items": evidence_items,
            "session_id": session_id,
        },
    )
