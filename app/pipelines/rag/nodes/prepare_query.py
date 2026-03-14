from __future__ import annotations

import time

from app.pipelines.rag.state import RagState
from app.services.retrieval_service import RetrievalService


def make_prepare_query_node(retrieval_service: RetrievalService):
    def node(state: RagState) -> RagState:
        started = time.perf_counter()
        query = state["user_query"].strip()
        metrics = dict(state.get("metrics", {}))
        metrics["latency_ms_prepare"] = int((time.perf_counter() - started) * 1000)
        return {
            "user_query": query,
            "metrics": metrics,
        }

    return node
