from __future__ import annotations

from dataclasses import dataclass

from app.adapters.auth.base import AuthProvider
from app.adapters.model_clients.base import EmbeddingClient, LLMClient, RerankerClient
from app.adapters.object_store.base import ObjectStore
from app.adapters.vector_store.base import VectorStore
from app.config import Settings


@dataclass(slots=True)
class SharedServices:
    settings: Settings
    auth_provider: AuthProvider
    object_store: ObjectStore
    vector_store: VectorStore
    embedding_client: EmbeddingClient
    reranker_client: RerankerClient
    llm_client: LLMClient

