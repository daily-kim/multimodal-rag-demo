from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.web.dependencies import get_current_context, get_monitoring_service

router = APIRouter(tags=["monitoring-partials"])


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/partials/monitoring/jobs/table", response_class=HTMLResponse)
async def monitoring_jobs_table(request: Request, current=Depends(get_current_context), monitoring_service=Depends(get_monitoring_service)):
    return _templates(request).TemplateResponse(
        "partials/monitoring_job_table.html",
        {"request": request, "current_user": current, "jobs": monitoring_service.recent_jobs(limit=50)},
    )


@router.get("/partials/monitoring/chats/table", response_class=HTMLResponse)
async def monitoring_chats_table(request: Request, current=Depends(get_current_context), monitoring_service=Depends(get_monitoring_service)):
    return _templates(request).TemplateResponse(
        "partials/monitoring_chat_table.html",
        {"request": request, "current_user": current, "chat_traces": monitoring_service.recent_chats(limit=50)},
    )

