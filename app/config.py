from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "mm-rag-demo"
    app_env: Literal["local", "production", "test"] = "local"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    secret_key: str = "local-dev-change-me"
    timezone: str = "Asia/Seoul"

    auth_provider: Literal["github"] = "github"
    auth_bypass: bool = False
    github_client_id: str = ""
    github_client_secret: str = ""
    github_authorize_url: str = "https://github.com/login/oauth/authorize"
    github_access_token_url: str = "https://github.com/login/oauth/access_token"
    github_user_api_url: str = "https://api.github.com/user"
    session_cookie_name: str = "mm_rag_demo_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_cookie_httponly: bool = True

    db_backend: Literal["sqlite", "mysql"] = "sqlite"
    sqlite_path: str = "./data/app.db"
    mysql_host: str = ""
    mysql_port: int = 3306
    mysql_db: str = ""
    mysql_user: str = ""
    mysql_password: str = ""

    object_store_backend: Literal["filesystem", "s3"] = "filesystem"
    filesystem_storage_root: str = "./data"
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = ""
    s3_force_path_style: bool = True

    vector_backend: Literal["nano", "elasticsearch"] = "nano"
    nano_vector_path: str = "./data/vector_store"
    es_host: str = ""
    es_username: str = ""
    es_password: str = ""
    es_index_prefix: str = "mm_rag_demo"

    embedding_api_base: str = Field(
        default="",
        validation_alias=AliasChoices("EMBEDDING_API_BASE", "OPENROUTER_API_BASE"),
    )
    embedding_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("EMBEDDING_API_KEY", "OPENROUTER_API_KEY"),
    )
    embedding_model: str = Field(
        default="",
        validation_alias=AliasChoices("EMBEDDING_MODEL", "OPENROUTER_MODEL"),
    )
    reranker_api_base: str = Field(
        default="",
        validation_alias=AliasChoices("RERANKER_API_BASE"),
    )
    reranker_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("RERANKER_API_KEY"),
    )
    reranker_model: str = Field(
        default="",
        validation_alias=AliasChoices("RERANKER_MODEL"),
    )
    llm_api_base: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_BASE"),
    )
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY"),
    )
    llm_model: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_MODEL"),
    )

    ingest_max_file_mb: int = 100
    ingest_max_pages: int = 500
    ingest_max_attempts: int = 3
    ingest_worker_poll_seconds: int = 2
    ingest_batch_page_size: int = 8
    ocr_enabled: bool = True

    rag_default_top_k: int = 12
    rag_default_rerank_enabled: bool = True
    rag_default_rerank_top_n: int = 6
    rag_default_max_images_to_llm: int = 6
    rag_default_retrieval_mode: Literal["pages_only", "with_neighbors"] = "with_neighbors"
    rag_default_neighbor_window_n: int = 1

    otel_enabled: bool = True
    otel_service_name: str = "mm-rag-demo"
    otel_exporter_otlp_endpoint: str = ""
    log_level: str = "INFO"
    log_json: bool = True

    @field_validator("log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def _validate_runtime(self) -> "Settings":
        if not self.session_cookie_httponly:
            raise ValueError("SESSION_COOKIE_HTTPONLY cannot be disabled with the current session middleware.")

        if self.app_env == "production" and self.auth_bypass:
            raise ValueError("AUTH_BYPASS must be false in production.")

        if self.app_env == "production" and self.app_debug:
            raise ValueError("APP_DEBUG must be false in production.")

        if self.app_env == "production" and self.secret_key in {"", "change-me", "local-dev-change-me"}:
            raise ValueError("SECRET_KEY must be explicitly set in production.")

        if self.db_backend == "mysql":
            required = [self.mysql_host, self.mysql_db, self.mysql_user]
            if not all(required):
                raise ValueError("MySQL backend requires MYSQL_HOST, MYSQL_DB, and MYSQL_USER.")

        if self.object_store_backend == "s3":
            required = [self.s3_bucket, self.s3_access_key, self.s3_secret_key]
            if not all(required):
                raise ValueError("S3 backend requires S3_BUCKET, S3_ACCESS_KEY, and S3_SECRET_KEY.")

        return self

    @computed_field
    @property
    def base_dir(self) -> Path:
        return Path.cwd()

    @computed_field
    @property
    def storage_root(self) -> Path:
        return (self.base_dir / self.filesystem_storage_root).resolve()

    @computed_field
    @property
    def vector_root(self) -> Path:
        return (self.base_dir / self.nano_vector_path).resolve()

    @computed_field
    @property
    def database_url(self) -> str:
        if self.db_backend == "sqlite":
            db_path = (self.base_dir / self.sqlite_path).resolve()
            return f"sqlite:///{db_path}"
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
        )

    @computed_field
    @property
    def max_upload_bytes(self) -> int:
        return self.ingest_max_file_mb * 1024 * 1024

    @property
    def supported_upload_extensions(self) -> tuple[str, ...]:
        return ("pdf", "txt", "md", "doc", "docx", "ppt", "pptx")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
