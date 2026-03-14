from __future__ import annotations

from pathlib import Path

import httpx

from app.adapters.model_clients.embedding_openai import OpenAICompatibleEmbeddingClient


class _DummyResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_openrouter_embedding_request_uses_image_content_payload(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"fake-image")
    captured: dict[str, object] = {}

    def fake_post(self, url: str, *, json: dict, headers: dict[str, str]) -> _DummyResponse:
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _DummyResponse({"data": [{"embedding": [0.1, 0.2, 0.3]}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    client = OpenAICompatibleEmbeddingClient(
        api_base="https://openrouter.ai",
        api_key="test-key",
        model="openai/clip-vit-large-patch14",
        app_name="mm-rag-demo",
    )

    embeddings = client.embed_images([str(image_path)])

    assert embeddings == [[0.1, 0.2, 0.3]]
    assert captured["url"] == "https://openrouter.ai/api/v1/embeddings"
    assert captured["headers"] == {
        "Authorization": "Bearer test-key",
        "X-Title": "mm-rag-demo",
    }

    payload = captured["json"]
    assert isinstance(payload, dict)
    assert payload["model"] == "openai/clip-vit-large-patch14"

    input_items = payload["input"]
    assert isinstance(input_items, list)
    first_item = input_items[0]
    assert first_item["content"][0]["type"] == "image_url"
    assert first_item["content"][0]["image_url"]["url"].startswith("data:image/png;base64,")


def test_non_openrouter_embedding_request_preserves_data_url_payload(monkeypatch, tmp_path) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"fake-image")
    captured: dict[str, object] = {}

    def fake_post(self, url: str, *, json: dict, headers: dict[str, str]) -> _DummyResponse:
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _DummyResponse({"data": [{"embedding": [0.5, 0.6]}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    client = OpenAICompatibleEmbeddingClient(
        api_base="https://example-embeddings.local/v1",
        api_key="test-key",
        model="demo-embedding-model",
    )

    embeddings = client.embed_images([str(image_path)])

    assert embeddings == [[0.5, 0.6]]
    assert captured["url"] == "https://example-embeddings.local/v1/embeddings"
    assert captured["headers"] == {"Authorization": "Bearer test-key"}

    payload = captured["json"]
    assert isinstance(payload, dict)
    assert payload["input"][0].startswith("data:image/png;base64,")


def test_openrouter_text_embedding_request_uses_plain_text_input(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(self, url: str, *, json: dict, headers: dict[str, str]) -> _DummyResponse:
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _DummyResponse({"data": [{"embedding": [0.7, 0.8, 0.9]}]})

    monkeypatch.setattr(httpx.Client, "post", fake_post)

    client = OpenAICompatibleEmbeddingClient(
        api_base="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="openai/clip-vit-large-patch14",
        app_name="mm-rag-demo",
    )

    embeddings = client.embed_texts(["hello world"])

    assert embeddings == [[0.7, 0.8, 0.9]]
    assert captured["url"] == "https://openrouter.ai/api/v1/embeddings"
    assert captured["headers"] == {
        "Authorization": "Bearer test-key",
        "X-Title": "mm-rag-demo",
    }

    payload = captured["json"]
    assert isinstance(payload, dict)
    assert payload["input"] == ["hello world"]
