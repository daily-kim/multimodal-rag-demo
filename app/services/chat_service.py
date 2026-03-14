from __future__ import annotations

import json
import time
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm import Session

from app.adapters.model_clients.base import LLMClient, LLMMessage
from app.config import Settings
from app.db.repositories.chats import ChatRepository
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.traces import TraceRepository
from app.domain.enums import ChatRole, EventSeverity
from app.domain.exceptions import NotFoundError, ValidationError
from app.domain.schemas.auth import CurrentUserContext
from app.domain.schemas.chat import ChatRequest, ChatResponse, EvidenceItem, RetrievalConfig
from app.pipelines.rag.graph import build_rag_preparation_graph
from app.services.retrieval_service import RetrievalService
from app.services.storage_service import StorageService
from app.utils.time import utcnow


@dataclass(slots=True)
class PreparedChatTurn:
    session_id: str
    user_message_id: str
    message: str
    selected_document_ids: list[str]
    retrieval_config: RetrievalConfig


@dataclass(slots=True)
class ChatStreamEvent:
    event: str
    data: dict[str, object]


class ChatService:
    def __init__(
        self,
        db: Session,
        *,
        settings: Settings,
        retrieval_service: RetrievalService,
        llm_client: LLMClient,
        storage: StorageService,
    ) -> None:
        self.db = db
        self.settings = settings
        self.retrieval_service = retrieval_service
        self.llm_client = llm_client
        self.storage = storage
        self.chats = ChatRepository(db)
        self.documents = DocumentRepository(db)
        self.traces = TraceRepository(db)

    def create_session(self, context: CurrentUserContext, *, selected_document_ids: list[str] | None = None):
        selected_document_ids = selected_document_ids or []
        self._validate_selected_documents(context.space_id, selected_document_ids)
        session = self.chats.create_session(
            space_id=context.space_id,
            user_id=context.user_id,
            selected_document_ids_json=json.dumps(selected_document_ids),
        )
        self.db.commit()
        return session

    def resolve_session(
        self,
        context: CurrentUserContext,
        *,
        session_id: str | None = None,
        force_new: bool = False,
        selected_document_ids: list[str] | None = None,
    ):
        if force_new:
            return self.create_session(context, selected_document_ids=selected_document_ids)
        if session_id:
            return self.get_session(context, session_id)
        session = self.chats.get_latest_session_for_user(space_id=context.space_id, user_id=context.user_id)
        if session is not None:
            return session
        return self.create_session(context, selected_document_ids=selected_document_ids)

    def list_recent_sessions(self, context: CurrentUserContext, *, limit: int = 20):
        return self.chats.list_recent_sessions_for_user(space_id=context.space_id, user_id=context.user_id, limit=limit)

    def get_session(self, context: CurrentUserContext, session_id: str):
        session = self.chats.get_session_in_space(context.space_id, session_id)
        if session is None:
            raise NotFoundError("Chat session not found.")
        return session

    def list_messages(self, context: CurrentUserContext, session_id: str):
        session = self.get_session(context, session_id)
        return self.chats.list_messages(session.id)

    def delete_session(self, context: CurrentUserContext, session_id: str) -> None:
        session = self.get_session(context, session_id)
        self.traces.delete_for_chat_session(session.id)
        self.chats.delete_messages_for_session(session.id)
        self.chats.delete_session(session)
        self.traces.create_event(
            space_id=context.space_id,
            user_id=context.user_id,
            event_type="chat.session_deleted",
            severity=EventSeverity.INFO,
            trace_id=None,
            payload_json=json.dumps({"chat_session_id": session.id, "title": session.title}),
        )
        self.db.commit()

    def clear_sessions(self, context: CurrentUserContext) -> int:
        sessions = self.list_recent_sessions(context, limit=500)
        if not sessions:
            return 0
        session_ids = [session.id for session in sessions]
        self.traces.delete_for_chat_sessions(session_ids)
        for session in sessions:
            self.chats.delete_messages_for_session(session.id)
            self.chats.delete_session(session)
        self.traces.create_event(
            space_id=context.space_id,
            user_id=context.user_id,
            event_type="chat.sessions_cleared",
            severity=EventSeverity.INFO,
            trace_id=None,
            payload_json=json.dumps({"chat_session_ids": session_ids, "count": len(session_ids)}),
        )
        self.db.commit()
        return len(session_ids)

    def post_message(self, context: CurrentUserContext, session_id: str, payload: ChatRequest) -> ChatResponse:
        session, user_message = self._create_user_message(context, session_id, payload, commit=False)
        state = self._prepare_generation_state(
            context=context,
            session_id=session.id,
            user_message_id=user_message.id,
            message=payload.message,
            selected_document_ids=payload.selected_document_ids,
            retrieval_config=payload.retrieval_config,
        )
        started = time.perf_counter()
        response = self.llm_client.chat(state.get("llm_messages", []), images=state.get("context_image_paths", []))
        metrics = dict(state.get("metrics", {}))
        metrics["latency_ms_generate"] = int((time.perf_counter() - started) * 1000)
        state["metrics"] = self._finalize_metrics(metrics)
        state["llm_answer"] = response.content
        state["llm_model_name"] = response.model_name
        self._persist_result(
            context=context,
            session=session,
            user_message_id=user_message.id,
            message=payload.message,
            selected_document_ids=payload.selected_document_ids,
            retrieval_config=payload.retrieval_config,
            state=state,
        )
        self.db.commit()
        evidence = [EvidenceItem.model_validate(item) for item in state["evidence_items"]]
        return ChatResponse(session_id=session.id, trace_id=state["trace_id"], answer=state["llm_answer"], evidence_items=evidence)

    def prepare_stream_message(self, context: CurrentUserContext, session_id: str, payload: ChatRequest) -> PreparedChatTurn:
        session, user_message = self._create_user_message(context, session_id, payload, commit=True)
        return PreparedChatTurn(
            session_id=session.id,
            user_message_id=user_message.id,
            message=payload.message,
            selected_document_ids=list(payload.selected_document_ids),
            retrieval_config=payload.retrieval_config,
        )

    def stream_message(self, context: CurrentUserContext, session_id: str, user_message_id: str):
        session = self.get_session(context, session_id)
        user_message = self.chats.get_message_in_session(session.id, user_message_id)
        if user_message is None or user_message.role != ChatRole.USER:
            raise NotFoundError("User message not found.")

        retrieval_config = RetrievalConfig.model_validate_json(user_message.retrieval_config_json or "{}")
        selected_document_ids = json.loads(session.selected_document_ids_json or "[]")
        yield ChatStreamEvent(event="status", data={"label": "Finding relevant pages and evidence..."})
        state = self._prepare_generation_state(
            context=context,
            session_id=session.id,
            user_message_id=user_message.id,
            message=user_message.content,
            selected_document_ids=selected_document_ids,
            retrieval_config=retrieval_config,
        )

        yield ChatStreamEvent(event="meta", data={"trace_id": state["trace_id"]})
        yield ChatStreamEvent(event="status", data={"label": "Generating answer..."})
        chunks: list[str] = []
        started = time.perf_counter()
        try:
            for chunk in self.llm_client.chat_stream(state.get("llm_messages", []), images=state.get("context_image_paths", [])):
                chunks.append(chunk)
                yield ChatStreamEvent(event="chunk", data={"text": chunk})
            metrics = dict(state.get("metrics", {}))
            metrics["latency_ms_generate"] = int((time.perf_counter() - started) * 1000)
            state["metrics"] = self._finalize_metrics(metrics)
            state["llm_answer"] = "".join(chunks).strip()
            state["llm_model_name"] = self.settings.llm_model or "streaming-model"
            yield ChatStreamEvent(event="status", data={"label": "Saving evidence and trace..."})
            self._persist_result(
                context=context,
                session=session,
                user_message_id=user_message.id,
                message=user_message.content,
                selected_document_ids=selected_document_ids,
                retrieval_config=retrieval_config,
                state=state,
            )
            self.db.commit()
            yield ChatStreamEvent(event="done", data={"trace_id": state["trace_id"]})
        except Exception as exc:
            self.db.rollback()
            self.traces.create_event(
                space_id=context.space_id,
                user_id=context.user_id,
                event_type="chat.failed",
                severity=EventSeverity.ERROR,
                trace_id=state.get("trace_id"),
                payload_json=json.dumps({"chat_session_id": session.id, "error": str(exc)}),
            )
            self.db.commit()
            yield ChatStreamEvent(event="chat_error", data={"message": "An error occurred while generating the answer."})

    def _build_chat_history(self, session_id: str, *, exclude_message_id: str | None = None, limit: int = 12) -> list[LLMMessage]:
        messages = self.chats.list_messages(session_id)
        filtered = [
            message
            for message in messages
            if message.id != exclude_message_id and message.role in {ChatRole.USER, ChatRole.ASSISTANT, ChatRole.SYSTEM}
        ]
        trimmed = filtered[-limit:]
        return [LLMMessage(role=message.role.value, content=message.content) for message in trimmed]

    def _create_user_message(
        self,
        context: CurrentUserContext,
        session_id: str,
        payload: ChatRequest,
        *,
        commit: bool,
    ):
        session = self.get_session(context, session_id)
        self._validate_selected_documents(context.space_id, payload.selected_document_ids)
        user_message = self.chats.add_message(
            chat_session_id=session.id,
            role=ChatRole.USER,
            content=payload.message,
            retrieval_config_json=payload.retrieval_config.model_dump_json(),
            trace_id=None,
        )
        if not session.title:
            session.title = self._build_session_title(payload.message)
        session.selected_document_ids_json = json.dumps(payload.selected_document_ids)
        session.updated_at = utcnow()
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return session, user_message

    def _prepare_generation_state(
        self,
        *,
        context: CurrentUserContext,
        session_id: str,
        user_message_id: str,
        message: str,
        selected_document_ids: list[str],
        retrieval_config: RetrievalConfig,
    ) -> dict:
        chat_history_messages = self._build_chat_history(session_id, exclude_message_id=user_message_id)
        graph = build_rag_preparation_graph(
            settings=self.settings,
            retrieval_service=self.retrieval_service,
            storage=self.storage,
        )
        return graph.invoke(
            {
                "trace_id": uuid4().hex,
                "space_id": context.space_id,
                "user_id": context.user_id,
                "chat_session_id": session_id,
                "user_query": message,
                "chat_history_messages": chat_history_messages,
                "selected_document_ids": selected_document_ids,
                "retrieval_mode": retrieval_config.retrieval_mode.value,
                "top_k": retrieval_config.top_k,
                "rerank_enabled": retrieval_config.rerank_enabled,
                "rerank_top_n": retrieval_config.rerank_top_n,
                "max_images_to_llm": retrieval_config.max_images_to_llm,
                "neighbor_window_n": retrieval_config.neighbor_window_n,
            }
        )

    def _persist_result(
        self,
        *,
        context: CurrentUserContext,
        session,
        user_message_id: str,
        message: str,
        selected_document_ids: list[str],
        retrieval_config: RetrievalConfig,
        state: dict,
    ) -> None:
        trace_id = state["trace_id"]
        assistant_message = self.chats.add_message(
            chat_session_id=session.id,
            role=ChatRole.ASSISTANT,
            content=state["llm_answer"],
            model_name=state.get("llm_model_name"),
            retrieval_config_json=retrieval_config.model_dump_json(),
            trace_id=trace_id,
        )
        self.traces.create_trace(
            id=trace_id,
            space_id=context.space_id,
            chat_session_id=session.id,
            user_message_id=user_message_id,
            query_text=message,
            selected_document_ids_json=json.dumps(selected_document_ids),
            retrieval_mode=retrieval_config.retrieval_mode,
            top_k=retrieval_config.top_k,
            rerank_enabled=retrieval_config.rerank_enabled,
            rerank_top_n=retrieval_config.rerank_top_n,
            max_images_to_llm=retrieval_config.max_images_to_llm,
            neighbor_window_n=retrieval_config.neighbor_window_n,
            retrieved_items_json=json.dumps(state["retrieved_hits"]),
            reranked_items_json=json.dumps(state["reranked_hits"]),
            final_context_items_json=json.dumps(state["final_context_hits"]),
            llm_request_summary_json=json.dumps(
                {"model": state.get("llm_model_name"), "image_count": len(state.get("context_image_paths", []))}
            ),
            answer_preview=state["llm_answer"][:300],
            latency_ms_total=state["metrics"].get("latency_ms_total"),
            latency_ms_retrieve=state["metrics"].get("latency_ms_retrieve"),
            latency_ms_rerank=state["metrics"].get("latency_ms_rerank"),
            latency_ms_generate=state["metrics"].get("latency_ms_generate"),
        )
        assistant_message.trace_id = trace_id
        self.traces.create_event(
            space_id=context.space_id,
            user_id=context.user_id,
            event_type="chat.completed",
            severity=EventSeverity.INFO,
            trace_id=trace_id,
            payload_json=json.dumps({"chat_session_id": session.id, "trace_id": trace_id}),
        )
        if not session.title:
            session.title = self._build_session_title(message)
        session.selected_document_ids_json = json.dumps(selected_document_ids)
        session.updated_at = utcnow()
        self.db.flush()

    def _finalize_metrics(self, metrics: dict[str, int]) -> dict[str, int]:
        finalized = dict(metrics)
        finalized["latency_ms_total"] = sum(value for key, value in finalized.items() if key.startswith("latency_ms_"))
        return finalized

    def _validate_selected_documents(self, space_id: str, document_ids: list[str]) -> None:
        if not document_ids:
            return
        found = self.documents.get_many_in_space(space_id, document_ids)
        if len(found) != len(set(document_ids)):
            raise ValidationError("Selected documents must belong to the current space.")

    @staticmethod
    def _build_session_title(message: str) -> str:
        normalized = " ".join(message.split()).strip()
        if len(normalized) <= 48:
            return normalized or "New chat"
        return f"{normalized[:45].rstrip()}..."
