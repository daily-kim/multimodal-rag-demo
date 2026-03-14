from __future__ import annotations

from app.pipelines.rag.state import RagState
from app.services.retrieval_service import RetrievalService


def make_retrieve_node(retrieval_service: RetrievalService):
    def node(state: RagState) -> RagState:
        query_vector, hits, latency_ms = retrieval_service.retrieve(
            space_id=state["space_id"],
            query=state["user_query"],
            selected_document_ids=state.get("selected_document_ids", []),
            top_k=state["top_k"],
        )
        metrics = dict(state.get("metrics", {}))
        metrics["latency_ms_retrieve"] = latency_ms
        return {
            "query_embedding": query_vector,
            "retrieved_hit_objects": hits,
            "retrieved_hits": [hit.to_trace_dict() for hit in hits],
            "metrics": metrics,
        }

    return node

