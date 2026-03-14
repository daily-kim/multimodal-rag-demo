from __future__ import annotations

from app.adapters.model_clients.base import LLMMessage
from app.adapters.model_clients.llm_openai import OpenAICompatibleLLMClient


def test_fallback_llm_does_not_echo_hidden_context() -> None:
    client = OpenAICompatibleLLMClient(api_base="", api_key="", model="")
    response = client.chat(
        [
            LLMMessage(role="system", content="Retrieved page context for this answer:\nsecret context"),
            LLMMessage(role="user", content="What does this document cover?"),
        ]
    )
    assert "secret context" not in response.content
    assert "What does this document cover?" in response.content
