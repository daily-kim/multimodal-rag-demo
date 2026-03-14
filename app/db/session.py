from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterator

from sqlalchemy import event
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.telemetry import instrument_sqlalchemy


@lru_cache(maxsize=8)
def _get_engine_cached(database_url: str, db_backend: str, otel_enabled: bool) -> Engine:
    connect_args = {"check_same_thread": False, "timeout": 30} if db_backend == "sqlite" else {}
    engine = create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
    if db_backend == "sqlite":
        _configure_sqlite_engine(engine)
    if otel_enabled:
        instrument_sqlalchemy(engine)
    return engine


def get_engine(settings: Settings | None = None) -> Engine:
    cfg = settings or get_settings()
    if cfg.db_backend == "sqlite":
        sqlite_path = (cfg.base_dir / cfg.sqlite_path).resolve()
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return _get_engine_cached(cfg.database_url, cfg.db_backend, cfg.otel_enabled)


@lru_cache(maxsize=8)
def _get_session_factory_cached(database_url: str, db_backend: str, otel_enabled: bool) -> sessionmaker[Session]:
    engine = _get_engine_cached(database_url, db_backend, otel_enabled)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    cfg = settings or get_settings()
    return _get_session_factory_cached(cfg.database_url, cfg.db_backend, cfg.otel_enabled)


def get_db_session() -> Iterator[Session]:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def _configure_sqlite_engine(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
