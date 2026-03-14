from __future__ import annotations

from collections.abc import Iterable

from app.adapters.model_clients.base import EmbeddingClient, LLMClient, LLMMessage, LLMResponse, RerankCandidate, RerankHit, RerankerClient


class FakeEmbeddingClient(EmbeddingClient):
    def __init__(self, dimensions: int = 8) -> None:
        self.dimensions = dimensions

    def embed_images(self, image_paths: list[str]) -> list[list[float]]:
        return [[float(index + 1)] * self.dimensions for index, _ in enumerate(image_paths)]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(index + 1)] * self.dimensions for index, _ in enumerate(texts)]


class FakeRerankerClient(RerankerClient):
    def rerank(self, query: str, candidates: list[RerankCandidate], top_n: int) -> list[RerankHit]:
        ordered = sorted(candidates, key=lambda item: len(item.text), reverse=True)
        return [RerankHit(id=item.id, score=float(len(item.text)), metadata=item.metadata) for item in ordered[:top_n]]


class FakeLLMClient(LLMClient):
    def __init__(self) -> None:
        self.last_messages: list[LLMMessage] = []
        self.streamed_messages: list[LLMMessage] = []

    def chat(self, messages: list[LLMMessage], images: list[str] | None = None, **kwargs) -> LLMResponse:
        self.last_messages = list(messages)
        prompt = messages[-1].content if messages else ""
        return LLMResponse(content=f"fake-answer: {prompt[:80]}", model_name="fake-llm")

    def chat_stream(self, messages: list[LLMMessage], images: list[str] | None = None, **kwargs) -> Iterable[str]:
        self.streamed_messages = list(messages)
        yield self.chat(messages, images=images, **kwargs).content
