from __future__ import annotations

from app.pipelines.rag.state import RagState
from app.services.retrieval_service import RetrievalService


def make_expand_neighbors_node(retrieval_service: RetrievalService):
    def node(state: RagState) -> RagState:
        source_hits = state.get("reranked_hit_objects") or state.get("retrieved_hit_objects", [])
        hits = retrieval_service.expand_neighbors(
            space_id=state["space_id"],
            hits=source_hits,
            window_n=state["neighbor_window_n"],
        )
        return {
            "expanded_hit_objects": hits,
            "expanded_hits": [hit.to_trace_dict() for hit in hits],
        }

    return node

