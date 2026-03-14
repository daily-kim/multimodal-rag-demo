from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_auth_bypass() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_bypass=True)


def test_uppercase_core_env_names_are_loaded(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_BYPASS", "true")
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("SECRET_KEY", "from-env")

    settings = Settings(_env_file=None)

    assert settings.auth_bypass is True
    assert settings.app_debug is True
    assert settings.secret_key == "from-env"


def test_production_rejects_insecure_secret_key() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="local-dev-change-me")


def test_session_cookie_httponly_cannot_be_disabled() -> None:
    with pytest.raises(ValidationError):
        Settings(session_cookie_httponly=False)


def test_sqlite_database_url_contains_resolved_path(tmp_path) -> None:
    settings = Settings(sqlite_path=str(tmp_path / "app.db"))
    assert settings.database_url.startswith("sqlite:///")
    assert str(tmp_path / "app.db") in settings.database_url


def test_openrouter_embedding_env_aliases(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_BASE", "https://openrouter.ai")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "demo-model")

    settings = Settings(_env_file=None)

    assert settings.embedding_api_base == "https://openrouter.ai"
    assert settings.embedding_api_key == "test-key"
    assert settings.embedding_model == "demo-model"


def test_llm_and_reranker_uppercase_env_names(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "openrouter/demo-model")
    monkeypatch.setenv("RERANKER_API_BASE", "https://example.test/v1")
    monkeypatch.setenv("RERANKER_API_KEY", "rerank-key")
    monkeypatch.setenv("RERANKER_MODEL", "demo-reranker")

    settings = Settings(_env_file=None)

    assert settings.llm_api_base == "https://openrouter.ai/api/v1"
    assert settings.llm_api_key == "test-key"
    assert settings.llm_model == "openrouter/demo-model"
    assert settings.reranker_api_base == "https://example.test/v1"
    assert settings.reranker_api_key == "rerank-key"
    assert settings.reranker_model == "demo-reranker"
