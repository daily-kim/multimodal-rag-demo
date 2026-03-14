from __future__ import annotations

import html
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import markdown as markdown_lib
from starlette.middleware.sessions import SessionMiddleware

from app.adapters.auth.bypass_auth import BypassAuthProvider
from app.adapters.auth.github_oauth import GitHubOAuthProvider
from app.adapters.model_clients.embedding_openai import OpenAICompatibleEmbeddingClient
from app.adapters.model_clients.llm_openai import OpenAICompatibleLLMClient
from app.adapters.model_clients.reranker_openai import OpenAICompatibleRerankerClient
from app.adapters.object_store.filesystem import FilesystemObjectStore
from app.adapters.object_store.s3 import S3ObjectStore
from app.adapters.vector_store.elasticsearch import ElasticsearchVectorStore
from app.adapters.vector_store.nano import NanoVectorStore
from app.config import get_settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_engine, get_session_factory
from app.domain.exceptions import AppError, AuthenticationError
from app.logging import configure_logging, get_logger
from app.services import SharedServices
from app.telemetry import instrument_fastapi, setup_telemetry
from app.web.routes import api_chat, api_documents, api_monitoring, auth, chat, documents, monitoring, pages


logger = get_logger(__name__)


def render_markdown(value: str) -> str:
    escaped = html.escape(value or "")
    return markdown_lib.markdown(
        escaped,
        extensions=["fenced_code", "tables", "sane_lists", "nl2br"],
    )


def create_shared_services(settings) -> SharedServices:
    if settings.auth_bypass:
        auth_provider = BypassAuthProvider()
    else:
        auth_provider = GitHubOAuthProvider(
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
            authorize_url=settings.github_authorize_url,
            access_token_url=settings.github_access_token_url,
            user_api_url=settings.github_user_api_url,
        )

    if settings.object_store_backend == "filesystem":
        object_store = FilesystemObjectStore(settings.storage_root)
    else:
        object_store = S3ObjectStore(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
            force_path_style=settings.s3_force_path_style,
        )

    if settings.vector_backend == "nano":
        vector_store = NanoVectorStore(settings.vector_root)
    else:
        vector_store = ElasticsearchVectorStore(
            settings.es_host,
            settings.es_username,
            settings.es_password,
            settings.es_index_prefix,
        )

    embedding_client = OpenAICompatibleEmbeddingClient(
        api_base=settings.embedding_api_base,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        app_name=settings.app_name,
    )
    reranker_client = OpenAICompatibleRerankerClient(
        api_base=settings.reranker_api_base,
        api_key=settings.reranker_api_key,
        model=settings.reranker_model,
    )
    llm_client = OpenAICompatibleLLMClient(
        api_base=settings.llm_api_base,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        app_name=settings.app_name,
    )
    return SharedServices(
        settings=settings,
        auth_provider=auth_provider,
        object_store=object_store,
        vector_store=vector_store,
        embedding_client=embedding_client,
        reranker_client=reranker_client,
        llm_client=llm_client,
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    setup_telemetry(settings)

    app = FastAPI(title=settings.app_name, debug=settings.app_debug)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie_name,
        same_site=settings.session_cookie_samesite,
        https_only=settings.session_cookie_secure,
        max_age=60 * 60 * 24 * 7,
    )

    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = get_session_factory(settings)
    app.state.shared = create_shared_services(settings)
    app.state.templates = Jinja2Templates(directory=str(Path(__file__).parent / "web" / "templates"))
    app.state.templates.env.filters["markdown"] = render_markdown
    app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "web" / "static")), name="static")

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or uuid4().hex
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        if exc.status_code == 401 and "text/html" in request.headers.get("accept", ""):
            return RedirectResponse(url="/login", status_code=303)
        if request.headers.get("HX-Request") == "true":
            return HTMLResponse(f"<div class='flash flash-error'>{exc.message}</div>", status_code=exc.status_code)
        return JSONResponse({"code": exc.code, "message": exc.message}, status_code=exc.status_code)

    @app.exception_handler(AuthenticationError)
    async def handle_auth_error(request: Request, exc: AuthenticationError):
        return RedirectResponse(url="/login", status_code=303)

    app.include_router(auth.router)
    app.include_router(pages.router)
    app.include_router(documents.router)
    app.include_router(chat.router)
    app.include_router(monitoring.router)
    app.include_router(api_documents.router)
    app.include_router(api_chat.router)
    app.include_router(api_monitoring.router)

    instrument_fastapi(app)
    return app


app = create_app()
