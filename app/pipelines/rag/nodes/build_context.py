from __future__ import annotations

from app.adapters.model_clients.base import LLMMessage
from app.pipelines.rag.state import RagState
from app.services.storage_service import StorageService


def make_build_context_node(storage: StorageService):
    def node(state: RagState) -> RagState:
        source_hits = (
            state.get("expanded_hit_objects")
            or state.get("reranked_hit_objects")
            or state.get("retrieved_hit_objects")
            or []
        )
        final_hits = source_hits[: state["max_images_to_llm"]]
        context_image_paths: list[str] = []
        context_lines: list[str] = []
        evidence_items: list[dict[str, object]] = []
        for hit in final_hits:
            image_input = storage.llm_image_input(hit.page.storage_image_path)
            if image_input:
                context_image_paths.append(image_input)
            context_text = (hit.page.extracted_text or "").strip()
            context_lines.append(
                f"- {hit.document.original_filename} page {hit.page.page_no}: {context_text[:400]}"
            )
            evidence_items.append(hit.to_trace_dict())
        history_messages = state.get("chat_history_messages", [])
        retrieved_context = "Retrieved page context for this answer:\n" + "\n".join(context_lines) if context_lines else "No retrieved text context."
        llm_messages = [
            LLMMessage(
                role="system",
                content=(
                    "You are an internal multimodal RAG assistant. "
                    "Answer based on the provided document pages and be explicit when evidence is weak. "
                    "Do not dump or quote the raw retrieved context verbatim in the answer body. "
                    "The UI shows evidence separately, so answer naturally and keep the response focused on the user's question.\n\n"
                    f"{retrieved_context}"
                ),
            ),
            *history_messages,
            LLMMessage(
                role="user",
                content=state["user_query"],
            ),
        ]
        return {
            "final_hit_objects": final_hits,
            "final_context_hits": [hit.to_trace_dict() for hit in final_hits],
            "evidence_items": evidence_items,
            "context_image_paths": context_image_paths,
            "llm_messages": llm_messages,
        }

    return node
