from __future__ import annotations

from langchain_core.messages import AIMessage, AIMessageChunk

from app.adapters.model_clients.base import LLMMessage
from app.adapters.model_clients.llm_openai import OpenAICompatibleLLMClient


class _FakeChatOpenAI:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.invocations: list[tuple[list[object], dict]] = []
        self.stream_invocations: list[tuple[list[object], dict]] = []

    def invoke(self, messages: list[object], **kwargs) -> AIMessage:
        self.invocations.append((messages, kwargs))
        return AIMessage(
            content="hello from model",
            response_metadata={"model": "openrouter/healer-alpha"},
        )

    def stream(self, messages: list[object], **kwargs):
        self.stream_invocations.append((messages, kwargs))
        yield AIMessageChunk(content="hello ")
        yield AIMessageChunk(content="stream")


def test_openrouter_langchain_adapter_invokes_chat_model(monkeypatch) -> None:
    monkeypatch.setattr("app.adapters.model_clients.llm_openai.ChatOpenAI", _FakeChatOpenAI)
    client = OpenAICompatibleLLMClient(
        api_base="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="openrouter/healer-alpha",
        app_name="mm-rag-demo",
    )

    response = client.chat(
        [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="assistant", content="Earlier answer."),
            LLMMessage(role="user", content="What changed?"),
        ]
    )

    assert response.content == "hello from model"
    assert response.model_name == "openrouter/healer-alpha"


def test_openrouter_langchain_adapter_streams_chunks(monkeypatch) -> None:
    monkeypatch.setattr("app.adapters.model_clients.llm_openai.ChatOpenAI", _FakeChatOpenAI)
    client = OpenAICompatibleLLMClient(
        api_base="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="openrouter/healer-alpha",
        app_name="mm-rag-demo",
    )

    chunks = list(client.chat_stream([LLMMessage(role="user", content="Say hi")]))

    assert chunks == ["hello ", "stream"]
