from __future__ import annotations

from app.pipelines.rag.state import RagState
from app.services.retrieval_service import RetrievalService


def make_rerank_node(retrieval_service: RetrievalService):
    def node(state: RagState) -> RagState:
        hits, latency_ms = retrieval_service.rerank(
            query=state["user_query"],
            hits=state.get("retrieved_hit_objects", []),
            top_n=state["rerank_top_n"],
        )
        metrics = dict(state.get("metrics", {}))
        metrics["latency_ms_rerank"] = latency_ms
        return {
            "reranked_hit_objects": hits,
            "reranked_hits": [hit.to_trace_dict() for hit in hits],
            "metrics": metrics,
        }

    return node

