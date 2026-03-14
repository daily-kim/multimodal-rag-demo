from __future__ import annotations

from app.adapters.model_clients.base import EmbeddingClient


def batch_embeddings(*, embedding_client: EmbeddingClient, image_paths: list[str], batch_size: int) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for start in range(0, len(image_paths), batch_size):
        embeddings.extend(embedding_client.embed_images(image_paths[start : start + batch_size]))
    return embeddings

