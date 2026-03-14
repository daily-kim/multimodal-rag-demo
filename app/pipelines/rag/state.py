from __future__ import annotations

from typing import Any, TypedDict


class RagState(TypedDict, total=False):
    trace_id: str
    space_id: str
    user_id: str
    chat_session_id: str
    user_query: str
    chat_history_messages: list[Any]
    selected_document_ids: list[str]
    retrieval_mode: str
    top_k: int
    rerank_enabled: bool
    rerank_top_n: int
    max_images_to_llm: int
    neighbor_window_n: int
    query_embedding: list[float]
    retrieved_hit_objects: list[Any]
    reranked_hit_objects: list[Any]
    expanded_hit_objects: list[Any]
    final_hit_objects: list[Any]
    retrieved_hits: list[dict[str, Any]]
    reranked_hits: list[dict[str, Any]]
    expanded_hits: list[dict[str, Any]]
    final_context_hits: list[dict[str, Any]]
    llm_messages: list[Any]
    llm_answer: str
    llm_model_name: str | None
    evidence_items: list[dict[str, Any]]
    context_image_paths: list[str]
    metrics: dict[str, int]
