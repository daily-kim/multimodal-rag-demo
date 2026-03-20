from __future__ import annotations

from types import SimpleNamespace

from app.domain.schemas.chat import RetrievalConfig
from app.web.routes.api_chat import _parse_chat_payload


class _FakeRequest:
    def __init__(self, settings) -> None:
        self.app = SimpleNamespace(state=SimpleNamespace(shared=SimpleNamespace(settings=settings)))


def test_retrieval_config_from_settings_uses_env_defaults() -> None:
    settings = SimpleNamespace(
        rag_default_top_k=9,
        rag_default_rerank_enabled=False,
        rag_default_rerank_top_n=4,
        rag_default_max_images_to_llm=11,
        rag_default_retrieval_mode="pages_only",
        rag_default_neighbor_window_n=2,
    )

    config = RetrievalConfig.from_settings(settings)

    assert config.top_k == 9
    assert config.rerank_enabled is False
    assert config.rerank_top_n == 4
    assert config.max_images_to_llm == 11
    assert config.retrieval_mode.value == "pages_only"
    assert config.neighbor_window_n == 2


def test_parse_chat_payload_uses_settings_max_images_default() -> None:
    settings = SimpleNamespace(
        rag_default_top_k=12,
        rag_default_rerank_enabled=True,
        rag_default_rerank_top_n=6,
        rag_default_max_images_to_llm=15,
        rag_default_retrieval_mode="with_neighbors",
        rag_default_neighbor_window_n=1,
    )
    request = _FakeRequest(settings)

    payload = _parse_chat_payload(request, {"message": "hello", "selected_document_ids": []})

    assert payload.retrieval_config.max_images_to_llm == 15
