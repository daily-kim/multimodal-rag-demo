from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.web.dependencies import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def auth_login(request: Request, auth_service=Depends(get_auth_service)):
    return auth_service.provider.get_login_redirect(request)


@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, auth_service=Depends(get_auth_service)):
    await auth_service.handle_callback(request)
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
async def auth_logout(request: Request, auth_service=Depends(get_auth_service)):
    await auth_service.logout(request)
    return RedirectResponse(url="/login", status_code=303)

