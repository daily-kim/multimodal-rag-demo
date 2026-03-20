from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from app.db.repositories.chats import ChatRepository
from app.db.repositories.traces import TraceRepository
from app.domain.exceptions import NotFoundError
from app.domain.schemas.chat import ChatRequest, RetrievalConfig
from app.web.dependencies import get_chat_service, get_current_context, get_db

router = APIRouter(prefix="/api", tags=["api-chat"])


def _parse_chat_payload(request: Request, data: dict) -> ChatRequest:
    settings = request.app.state.shared.settings
    defaults = RetrievalConfig.from_settings(settings)
    if "retrieval_config" in data:
        return ChatRequest.model_validate(data)
    retrieval = RetrievalConfig(
        top_k=int(data.get("top_k", defaults.top_k)),
        rerank_enabled=str(data.get("rerank_enabled", str(defaults.rerank_enabled))).lower() in {"1", "true", "on", "yes"},
        rerank_top_n=int(data.get("rerank_top_n", defaults.rerank_top_n)),
        max_images_to_llm=int(data.get("max_images_to_llm", defaults.max_images_to_llm)),
        retrieval_mode=data.get("retrieval_mode", defaults.retrieval_mode.value),
        neighbor_window_n=int(data.get("neighbor_window_n", defaults.neighbor_window_n)),
    )
    selected = data.get("selected_document_ids", [])
    if isinstance(selected, str):
        selected = [selected]
    return ChatRequest(message=data["message"], selected_document_ids=list(selected), retrieval_config=retrieval)


@router.post("/chat/sessions")
async def create_chat_session(request: Request, current=Depends(get_current_context), chat_service=Depends(get_chat_service)):
    payload = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    session = chat_service.create_session(current, selected_document_ids=payload.get("selected_document_ids", []))
    return {"session_id": session.id}


@router.get("/chat/sessions/{session_id}")
async def get_chat_session(session_id: str, current=Depends(get_current_context), chat_service=Depends(get_chat_service)):
    session = chat_service.get_session(current, session_id)
    return {
        "id": session.id,
        "title": session.title,
        "selected_document_ids_json": session.selected_document_ids_json,
    }


@router.post("/chat/sessions/{session_id}/delete")
async def delete_chat_session(
    session_id: str,
    request: Request,
    current=Depends(get_current_context),
    chat_service=Depends(get_chat_service),
):
    form = await request.form()
    return_session_id = str(form.get("return_session_id", "")).strip() or None
    chat_service.delete_session(current, session_id)
    redirect_url = "/chat"
    if return_session_id and return_session_id != session_id:
        try:
            chat_service.get_session(current, return_session_id)
            redirect_url = f"/chat?session_id={return_session_id}"
        except NotFoundError:
            redirect_url = "/chat"
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/chat/sessions/clear")
async def clear_chat_sessions(
    current=Depends(get_current_context),
    chat_service=Depends(get_chat_service),
):
    chat_service.clear_sessions(current)
    return RedirectResponse(url="/chat?new=1", status_code=303)


@router.post("/chat/sessions/{session_id}/messages")
async def post_chat_message(
    session_id: str,
    request: Request,
    current=Depends(get_current_context),
    chat_service=Depends(get_chat_service),
    db=Depends(get_db),
):
    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)
        data["selected_document_ids"] = form.getlist("selected_document_ids")
    payload = _parse_chat_payload(request, data)
    response = chat_service.post_message(current, session_id, payload)
    if request.headers.get("HX-Request") == "true":
        messages = ChatRepository(db).list_messages(session_id)
        return request.app.state.templates.TemplateResponse(
            "partials/chat_panel.html",
            {
                "request": request,
                "current_user": current,
                "chat_session": ChatRepository(db).get_session_in_space(current.space_id, session_id),
                "messages": messages,
                "latest_response": response,
                "retrieval_defaults": payload.retrieval_config,
            },
        )
    return response.model_dump()


@router.post("/chat/sessions/{session_id}/messages/stream-init")
async def init_stream_chat_message(
    session_id: str,
    request: Request,
    current=Depends(get_current_context),
    chat_service=Depends(get_chat_service),
):
    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)
        data["selected_document_ids"] = form.getlist("selected_document_ids")
    payload = _parse_chat_payload(request, data)
    prepared = chat_service.prepare_stream_message(current, session_id, payload)
    return {
        "session_id": prepared.session_id,
        "user_message_id": prepared.user_message_id,
        "stream_url": f"/api/chat/sessions/{prepared.session_id}/stream?user_message_id={prepared.user_message_id}",
    }


@router.get("/chat/sessions/{session_id}/stream")
async def stream_chat_session(
    session_id: str,
    request: Request,
    user_message_id: str,
    current=Depends(get_current_context),
    chat_service=Depends(get_chat_service),
):
    def sse(event: str, data: dict[str, object]) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def event_stream():
        for event in chat_service.stream_message(current, session_id, user_message_id):
            yield sse(event.event, event.data)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions/{session_id}/messages")
async def get_chat_messages(session_id: str, current=Depends(get_current_context), db=Depends(get_db)):
    session = ChatRepository(db).get_session_in_space(current.space_id, session_id)
    messages = ChatRepository(db).list_messages(session_id) if session else []
    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "trace_id": message.trace_id,
        }
        for message in messages
    ]


@router.get("/chat/traces/{trace_id}")
async def get_chat_trace(trace_id: str, current=Depends(get_current_context), db=Depends(get_db)):
    trace = TraceRepository(db).get_by_trace_id(trace_id)
    if trace is None or trace.space_id != current.space_id:
        return JSONResponse({"detail": "Trace not found."}, status_code=404)
    return {
        "id": trace.id,
        "query_text": trace.query_text,
        "retrieved_items_json": trace.retrieved_items_json,
        "final_context_items_json": trace.final_context_items_json,
        "answer_preview": trace.answer_preview,
    }
