from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(slots=True)
class RerankCandidate:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RerankHit:
    id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMMessage:
    role: str
    content: str


@dataclass(slots=True)
class LLMResponse:
    content: str
    model_name: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class EmbeddingClient(ABC):
    @abstractmethod
    def embed_images(self, image_paths: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class RerankerClient(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: list[RerankCandidate], top_n: int) -> list[RerankHit]:
        raise NotImplementedError


class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: list[LLMMessage], images: list[str] | None = None, **kwargs: Any) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    def chat_stream(self, messages: list[LLMMessage], images: list[str] | None = None, **kwargs: Any) -> Iterable[str]:
        raise NotImplementedError
