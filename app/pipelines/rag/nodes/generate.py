from __future__ import annotations

import time

from app.adapters.model_clients.base import LLMClient
from app.pipelines.rag.state import RagState


def make_generate_node(llm_client: LLMClient):
    def node(state: RagState) -> RagState:
        started = time.perf_counter()
        response = llm_client.chat(state.get("llm_messages", []), images=state.get("context_image_paths", []))
        metrics = dict(state.get("metrics", {}))
        metrics["latency_ms_generate"] = int((time.perf_counter() - started) * 1000)
        return {
            "llm_answer": response.content,
            "llm_model_name": response.model_name,
            "metrics": metrics,
        }

    return node

