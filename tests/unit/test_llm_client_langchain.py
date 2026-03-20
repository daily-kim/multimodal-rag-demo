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


def test_openrouter_langchain_adapter_attaches_images_to_last_user_message(monkeypatch) -> None:
    monkeypatch.setattr("app.adapters.model_clients.llm_openai.ChatOpenAI", _FakeChatOpenAI)
    monkeypatch.setattr("app.adapters.model_clients.llm_openai.file_to_data_url", lambda path: f"data://{path}")
    client = OpenAICompatibleLLMClient(
        api_base="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="openrouter/healer-alpha",
        app_name="mm-rag-demo",
    )

    client.chat(
        [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="assistant", content="Earlier answer."),
            LLMMessage(role="user", content="Use the provided pages."),
        ],
        images=["/tmp/page-1.png", "/tmp/page-2.png"],
    )

    payload_messages, _kwargs = client._get_chat_model().invocations[-1]
    last_message = payload_messages[-1]
    assert isinstance(last_message.content, list)
    assert last_message.content[0] == {"type": "text", "text": "Use the provided pages."}
    assert last_message.content[1:] == [
        {"type": "image_url", "image_url": {"url": "data:///tmp/page-1.png"}},
        {"type": "image_url", "image_url": {"url": "data:///tmp/page-2.png"}},
    ]


def test_openrouter_langchain_adapter_uses_remote_image_urls_as_is(monkeypatch) -> None:
    monkeypatch.setattr("app.adapters.model_clients.llm_openai.ChatOpenAI", _FakeChatOpenAI)
    monkeypatch.setattr("app.adapters.model_clients.llm_openai.file_to_data_url", lambda path: f"data://{path}")
    client = OpenAICompatibleLLMClient(
        api_base="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="openrouter/healer-alpha",
        app_name="mm-rag-demo",
    )

    client.chat(
        [LLMMessage(role="user", content="Use this image url.")],
        images=["https://s3.example.com/presigned-object?token=abc"],
    )

    payload_messages, _kwargs = client._get_chat_model().invocations[-1]
    last_message = payload_messages[-1]
    assert isinstance(last_message.content, list)
    assert last_message.content[1:] == [
        {"type": "image_url", "image_url": {"url": "https://s3.example.com/presigned-object?token=abc"}},
    ]
