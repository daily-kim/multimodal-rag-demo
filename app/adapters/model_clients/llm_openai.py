from __future__ import annotations

from collections.abc import Iterable

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.adapters.model_clients.base import LLMClient, LLMMessage, LLMResponse
from app.utils.images import file_to_data_url


class OpenAICompatibleLLMClient(LLMClient):
    def __init__(self, *, api_base: str, api_key: str, model: str, app_name: str | None = None) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.app_name = app_name
        self._chat_model: ChatOpenAI | None = None

    def _fallback_response(self, messages: list[LLMMessage]) -> LLMResponse:
        question = next((message.content for message in reversed(messages) if message.role == "user"), "")
        if question:
            content = f"[demo-response] No model server is configured, so the app is returning a local demo response.\n\nQuestion: {question}"
        else:
            content = "[demo-response] No model server is configured, so the app is returning a local demo response."
        return LLMResponse(content=content, model_name="local-fallback")

    def _get_chat_model(self) -> ChatOpenAI:
        if self._chat_model is None:
            kwargs = {
                "model": self.model,
                "api_key": self.api_key or None,
                "base_url": self.api_base or None,
                "timeout": 120,
                "max_retries": 2,
                "default_headers": {"X-Title": self.app_name} if self.app_name else None,
                "stream_usage": False,
            }
            self._chat_model = ChatOpenAI(**{key: value for key, value in kwargs.items() if value is not None})
        return self._chat_model

    def _content_to_text(self, content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "".join(parts)
        return str(content)

    @staticmethod
    def _image_reference_to_url(reference: str) -> str:
        if reference.startswith(("http://", "https://", "data:")):
            return reference
        return file_to_data_url(reference)

    def _to_langchain_messages(self, messages: list[LLMMessage], images: list[str] | None = None) -> list[SystemMessage | HumanMessage | AIMessage]:
        payload_messages: list[SystemMessage | HumanMessage | AIMessage] = []
        last_user_index = max((index for index, message in enumerate(messages) if message.role == "user"), default=-1)
        for index, message in enumerate(messages):
            content: object = message.content
            if images and index == last_user_index and message.role == "user":
                content = [
                    {"type": "text", "text": message.content},
                    *({"type": "image_url", "image_url": {"url": self._image_reference_to_url(path)}} for path in images),
                ]

            if message.role == "system":
                payload_messages.append(SystemMessage(content=content))
            elif message.role == "assistant":
                payload_messages.append(AIMessage(content=content))
            else:
                payload_messages.append(HumanMessage(content=content))
        return payload_messages

    def chat(self, messages: list[LLMMessage], images: list[str] | None = None, **kwargs) -> LLMResponse:
        if not self.api_base or not self.model:
            return self._fallback_response(messages)

        response = self._get_chat_model().invoke(self._to_langchain_messages(messages, images=images), **kwargs)
        return LLMResponse(
            content=self._content_to_text(response.content),
            model_name=response.response_metadata.get("model_name") or response.response_metadata.get("model"),
            raw_response={
                "response_metadata": response.response_metadata,
                "usage_metadata": getattr(response, "usage_metadata", None),
            },
        )

    def chat_stream(self, messages: list[LLMMessage], images: list[str] | None = None, **kwargs) -> Iterable[str]:
        if not self.api_base or not self.model:
            yield self._fallback_response(messages).content
            return

        for chunk in self._get_chat_model().stream(self._to_langchain_messages(messages, images=images), **kwargs):
            if isinstance(chunk, AIMessageChunk):
                text = self._content_to_text(chunk.content)
                if text:
                    yield text
