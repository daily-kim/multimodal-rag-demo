from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.repositories.traces import TraceRepository
from app.web.dependencies import get_current_context, get_db, get_monitoring_service

router = APIRouter(prefix="/api/monitoring", tags=["api-monitoring"])


@router.get("/jobs")
async def monitoring_jobs(current=Depends(get_current_context), monitoring_service=Depends(get_monitoring_service)):
    return [
        {
            "id": job.id,
            "document_id": job.document_id,
            "status": job.status,
            "step": job.step,
            "attempt_count": job.attempt_count,
            "trace_id": job.trace_id,
        }
        for job in monitoring_service.recent_jobs(limit=100)
        if job.space_id == current.space_id
    ]


@router.get("/chats")
async def monitoring_chats(current=Depends(get_current_context), monitoring_service=Depends(get_monitoring_service)):
    return [
        {
            "id": trace.id,
            "query_text": trace.query_text,
            "trace_id": trace.id,
            "latency_ms_total": trace.latency_ms_total,
        }
        for trace in monitoring_service.recent_chats(limit=100)
        if trace.space_id == current.space_id
    ]


@router.get("/events")
async def monitoring_events(current=Depends(get_current_context), monitoring_service=Depends(get_monitoring_service)):
    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "severity": event.severity,
            "trace_id": event.trace_id,
        }
        for event in monitoring_service.recent_events(limit=100)
        if event.space_id in {None, current.space_id}
    ]


@router.get("/trace/{trace_id}")
async def monitoring_trace(trace_id: str, current=Depends(get_current_context), db=Depends(get_db)):
    trace = TraceRepository(db).get_by_trace_id(trace_id)
    if trace is None or trace.space_id != current.space_id:
        return {"detail": "Trace not found."}
    return {
        "id": trace.id,
        "query_text": trace.query_text,
        "retrieved_items_json": trace.retrieved_items_json,
        "reranked_items_json": trace.reranked_items_json,
        "final_context_items_json": trace.final_context_items_json,
        "llm_request_summary_json": trace.llm_request_summary_json,
    }

