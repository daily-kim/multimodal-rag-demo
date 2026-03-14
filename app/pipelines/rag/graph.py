from __future__ import annotations

from typing import Callable

from langgraph.graph import END, StateGraph

from app.adapters.model_clients.base import LLMClient
from app.config import Settings
from app.pipelines.rag.nodes.build_context import make_build_context_node
from app.pipelines.rag.nodes.expand_neighbors import make_expand_neighbors_node
from app.pipelines.rag.nodes.finalize import make_finalize_node
from app.pipelines.rag.nodes.generate import make_generate_node
from app.pipelines.rag.nodes.prepare_query import make_prepare_query_node
from app.pipelines.rag.nodes.rerank import make_rerank_node
from app.pipelines.rag.nodes.retrieve import make_retrieve_node
from app.pipelines.rag.state import RagState
from app.services.retrieval_service import RetrievalService
from app.services.storage_service import StorageService


def build_rag_preparation_graph(
    *,
    settings: Settings,
    retrieval_service: RetrievalService,
    storage: StorageService,
):
    graph = StateGraph(RagState)
    graph.add_node("prepare_query", make_prepare_query_node(retrieval_service))
    graph.add_node("retrieve", make_retrieve_node(retrieval_service))
    graph.add_node("rerank", make_rerank_node(retrieval_service))
    graph.add_node("expand_neighbors", make_expand_neighbors_node(retrieval_service))
    graph.add_node("build_context", make_build_context_node(storage))
    graph.set_entry_point("prepare_query")
    graph.add_edge("prepare_query", "retrieve")

    def route_after_retrieve(state: RagState) -> str:
        if state.get("rerank_enabled"):
            return "rerank"
        return "expand_neighbors" if state.get("retrieval_mode") == "with_neighbors" else "build_context"

    def route_after_rerank(state: RagState) -> str:
        return "expand_neighbors" if state.get("retrieval_mode") == "with_neighbors" else "build_context"

    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"rerank": "rerank", "expand_neighbors": "expand_neighbors", "build_context": "build_context"},
    )
    graph.add_conditional_edges(
        "rerank",
        route_after_rerank,
        {"expand_neighbors": "expand_neighbors", "build_context": "build_context"},
    )
    graph.add_edge("expand_neighbors", "build_context")
    graph.add_edge("build_context", END)
    return graph.compile()


def build_rag_graph(
    *,
    settings: Settings,
    retrieval_service: RetrievalService,
    llm_client: LLMClient,
    storage: StorageService,
    persist_result: Callable[[dict], None],
):
    graph = StateGraph(RagState)
    graph.add_node("prepare_query", make_prepare_query_node(retrieval_service))
    graph.add_node("retrieve", make_retrieve_node(retrieval_service))
    graph.add_node("rerank", make_rerank_node(retrieval_service))
    graph.add_node("expand_neighbors", make_expand_neighbors_node(retrieval_service))
    graph.add_node("build_context", make_build_context_node(storage))
    graph.add_node("generate", make_generate_node(llm_client))
    graph.add_node("finalize", make_finalize_node(persist_result))
    graph.set_entry_point("prepare_query")
    graph.add_edge("prepare_query", "retrieve")

    def route_after_retrieve(state: RagState) -> str:
        if state.get("rerank_enabled"):
            return "rerank"
        return "expand_neighbors" if state.get("retrieval_mode") == "with_neighbors" else "build_context"

    def route_after_rerank(state: RagState) -> str:
        return "expand_neighbors" if state.get("retrieval_mode") == "with_neighbors" else "build_context"

    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"rerank": "rerank", "expand_neighbors": "expand_neighbors", "build_context": "build_context"},
    )
    graph.add_conditional_edges(
        "rerank",
        route_after_rerank,
        {"expand_neighbors": "expand_neighbors", "build_context": "build_context"},
    )
    graph.add_edge("expand_neighbors", "build_context")
    graph.add_edge("build_context", "generate")
    graph.add_edge("generate", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()
