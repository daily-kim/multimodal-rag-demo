from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.object_store.filesystem import FilesystemObjectStore
from app.adapters.vector_store.nano import NanoVectorStore
from app.config import Settings
from app.db.base import Base
from app.db.repositories.chats import ChatRepository
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.spaces import SpaceRepository
from app.db.repositories.traces import TraceRepository
from app.db.repositories.users import UserRepository
from app.domain.enums import ChatRole, DocumentSourceType, DocumentStatus, ExtractedTextSource
from app.domain.schemas.auth import CurrentUserContext
from app.domain.schemas.chat import ChatRequest, RetrievalConfig
from app.services.chat_service import ChatService
from app.services.retrieval_service import RetrievalService
from app.services.storage_service import StorageService
from tests.fakes import FakeEmbeddingClient, FakeLLMClient, FakeRerankerClient


def test_chat_flow_saves_trace_and_assistant_message(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    user = UserRepository(session).create(username="dev-user", display_name="Developer")
    space = SpaceRepository(session).create(user_id=user.id, name="Default", slug="default", is_default=True)
    session.flush()
    document = DocumentRepository(session).create(
        space_id=space.id,
        original_filename="demo.pdf",
        normalized_filename="document.pdf",
        file_ext="pdf",
        mime_type="application/pdf",
        source_type=DocumentSourceType.UPLOAD,
        status=DocumentStatus.READY,
        size_bytes=10,
        sha256="b" * 64,
        total_pages=1,
        storage_original_path="orig",
        storage_pdf_path="pdf",
        storage_thumbnail_path=None,
        created_by_user_id=user.id,
    )
    page = DocumentRepository(session).add_page(
        document_id=document.id,
        space_id=space.id,
        page_no=1,
        width=100,
        height=100,
        storage_image_path="missing.png",
        storage_thumbnail_path=None,
        extracted_text="The capital of France is Paris.",
        extracted_text_source=ExtractedTextSource.NATIVE,
        checksum="c",
    )
    session.commit()

    settings = Settings(
        sqlite_path=str(tmp_path / "app.db"),
        filesystem_storage_root=str(tmp_path / "data"),
        nano_vector_path=str(tmp_path / "vectors"),
        embedding_api_base="",
    )
    storage = StorageService(FilesystemObjectStore(tmp_path / "data"))
    retrieval_service = RetrievalService(
        session,
        NanoVectorStore(tmp_path / "vectors"),
        FakeRerankerClient(),
        FakeEmbeddingClient(),
        settings,
    )
    llm_client = FakeLLMClient()
    chat_service = ChatService(
        session,
        settings=settings,
        retrieval_service=retrieval_service,
        llm_client=llm_client,
        storage=storage,
    )
    context = CurrentUserContext(user_id=user.id, space_id=space.id, username=user.username, display_name=user.display_name)
    chat_session = chat_service.create_session(context, selected_document_ids=[document.id])
    response = chat_service.post_message(
        context,
        chat_session.id,
        ChatRequest(
            message="What is the capital of France?",
            selected_document_ids=[document.id],
            retrieval_config=RetrievalConfig(),
        ),
    )

    messages = ChatRepository(session).list_messages(chat_session.id)
    assert any(message.role == ChatRole.ASSISTANT for message in messages)
    trace = TraceRepository(session).get_by_trace_id(response.trace_id)
    assert trace is not None
    assert json.loads(trace.final_context_items_json)[0]["page_no"] == 1
    assert json.loads(trace.final_context_items_json)[0]["context_text"] == "The capital of France is Paris."
    assert llm_client.last_messages[-1].content == "What is the capital of France?"


def test_chat_flow_includes_prior_history_in_model_messages(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    user = UserRepository(session).create(username="dev-user", display_name="Developer")
    space = SpaceRepository(session).create(user_id=user.id, name="Default", slug="default", is_default=True)
    session.flush()
    document = DocumentRepository(session).create(
        space_id=space.id,
        original_filename="demo.pdf",
        normalized_filename="document.pdf",
        file_ext="pdf",
        mime_type="application/pdf",
        source_type=DocumentSourceType.UPLOAD,
        status=DocumentStatus.READY,
        size_bytes=10,
        sha256="b" * 64,
        total_pages=1,
        storage_original_path="orig",
        storage_pdf_path="pdf",
        storage_thumbnail_path=None,
        created_by_user_id=user.id,
    )
    DocumentRepository(session).add_page(
        document_id=document.id,
        space_id=space.id,
        page_no=1,
        width=100,
        height=100,
        storage_image_path="missing.png",
        storage_thumbnail_path=None,
        extracted_text="Paris is the capital of France.",
        extracted_text_source=ExtractedTextSource.NATIVE,
        checksum="c",
    )
    session.commit()

    settings = Settings(
        sqlite_path=str(tmp_path / "app.db"),
        filesystem_storage_root=str(tmp_path / "data"),
        nano_vector_path=str(tmp_path / "vectors"),
        embedding_api_base="",
    )
    storage = StorageService(FilesystemObjectStore(tmp_path / "data"))
    retrieval_service = RetrievalService(
        session,
        NanoVectorStore(tmp_path / "vectors"),
        FakeRerankerClient(),
        FakeEmbeddingClient(),
        settings,
    )
    llm_client = FakeLLMClient()
    chat_service = ChatService(
        session,
        settings=settings,
        retrieval_service=retrieval_service,
        llm_client=llm_client,
        storage=storage,
    )
    context = CurrentUserContext(user_id=user.id, space_id=space.id, username=user.username, display_name=user.display_name)
    chat_session = chat_service.create_session(context, selected_document_ids=[document.id])
    chat_service.post_message(
        context,
        chat_session.id,
        ChatRequest(
            message="First question",
            selected_document_ids=[document.id],
            retrieval_config=RetrievalConfig(),
        ),
    )
    chat_service.post_message(
        context,
        chat_session.id,
        ChatRequest(
            message="Summarize the previous answer in one sentence.",
            selected_document_ids=[document.id],
            retrieval_config=RetrievalConfig(),
        ),
    )

    history_texts = [message.content for message in llm_client.last_messages]
    assert "First question" in history_texts
    assert "fake-answer: First question" in history_texts
    assert history_texts[-1] == "Summarize the previous answer in one sentence."


def test_chat_service_reuses_latest_session_and_keeps_history(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    user = UserRepository(session).create(username="dev-user", display_name="Developer")
    space = SpaceRepository(session).create(user_id=user.id, name="Default", slug="default", is_default=True)
    session.flush()
    document = DocumentRepository(session).create(
        space_id=space.id,
        original_filename="demo.pdf",
        normalized_filename="document.pdf",
        file_ext="pdf",
        mime_type="application/pdf",
        source_type=DocumentSourceType.UPLOAD,
        status=DocumentStatus.READY,
        size_bytes=10,
        sha256="b" * 64,
        total_pages=1,
        storage_original_path="orig",
        storage_pdf_path="pdf",
        storage_thumbnail_path=None,
        created_by_user_id=user.id,
    )
    DocumentRepository(session).add_page(
        document_id=document.id,
        space_id=space.id,
        page_no=1,
        width=100,
        height=100,
        storage_image_path="missing.png",
        storage_thumbnail_path=None,
        extracted_text="Paris is the capital of France.",
        extracted_text_source=ExtractedTextSource.NATIVE,
        checksum="c",
    )
    session.commit()

    settings = Settings(
        sqlite_path=str(tmp_path / "app.db"),
        filesystem_storage_root=str(tmp_path / "data"),
        nano_vector_path=str(tmp_path / "vectors"),
        embedding_api_base="",
    )
    storage = StorageService(FilesystemObjectStore(tmp_path / "data"))
    retrieval_service = RetrievalService(
        session,
        NanoVectorStore(tmp_path / "vectors"),
        FakeRerankerClient(),
        FakeEmbeddingClient(),
        settings,
    )
    chat_service = ChatService(
        session,
        settings=settings,
        retrieval_service=retrieval_service,
        llm_client=FakeLLMClient(),
        storage=storage,
    )
    context = CurrentUserContext(user_id=user.id, space_id=space.id, username=user.username, display_name=user.display_name)

    initial_session = chat_service.resolve_session(context)
    chat_service.post_message(
        context,
        initial_session.id,
        ChatRequest(
            message="Summarize our company insurance document.",
            selected_document_ids=[document.id],
            retrieval_config=RetrievalConfig(),
        ),
    )

    reopened_session = chat_service.resolve_session(context)
    reopened_messages = chat_service.list_messages(context, reopened_session.id)

    assert reopened_session.id == initial_session.id
    assert reopened_session.title == "Summarize our company insurance document."
    assert len(reopened_messages) == 2

    fresh_session = chat_service.resolve_session(context, force_new=True)

    assert fresh_session.id != reopened_session.id


def test_chat_service_delete_session_removes_messages_and_traces(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    user = UserRepository(session).create(username="dev-user", display_name="Developer")
    space = SpaceRepository(session).create(user_id=user.id, name="Default", slug="default", is_default=True)
    session.flush()
    document = DocumentRepository(session).create(
        space_id=space.id,
        original_filename="demo.pdf",
        normalized_filename="document.pdf",
        file_ext="pdf",
        mime_type="application/pdf",
        source_type=DocumentSourceType.UPLOAD,
        status=DocumentStatus.READY,
        size_bytes=10,
        sha256="b" * 64,
        total_pages=1,
        storage_original_path="orig",
        storage_pdf_path="pdf",
        storage_thumbnail_path=None,
        created_by_user_id=user.id,
    )
    DocumentRepository(session).add_page(
        document_id=document.id,
        space_id=space.id,
        page_no=1,
        width=100,
        height=100,
        storage_image_path="missing.png",
        storage_thumbnail_path=None,
        extracted_text="Paris is the capital of France.",
        extracted_text_source=ExtractedTextSource.NATIVE,
        checksum="c",
    )
    session.commit()

    settings = Settings(
        sqlite_path=str(tmp_path / "app.db"),
        filesystem_storage_root=str(tmp_path / "data"),
        nano_vector_path=str(tmp_path / "vectors"),
        embedding_api_base="",
    )
    storage = StorageService(FilesystemObjectStore(tmp_path / "data"))
    retrieval_service = RetrievalService(
        session,
        NanoVectorStore(tmp_path / "vectors"),
        FakeRerankerClient(),
        FakeEmbeddingClient(),
        settings,
    )
    chat_service = ChatService(
        session,
        settings=settings,
        retrieval_service=retrieval_service,
        llm_client=FakeLLMClient(),
        storage=storage,
    )
    context = CurrentUserContext(user_id=user.id, space_id=space.id, username=user.username, display_name=user.display_name)

    chat_session = chat_service.create_session(context, selected_document_ids=[document.id])
    response = chat_service.post_message(
        context,
        chat_session.id,
        ChatRequest(
            message="Delete this conversation.",
            selected_document_ids=[document.id],
            retrieval_config=RetrievalConfig(),
        ),
    )

    chat_service.delete_session(context, chat_session.id)

    assert ChatRepository(session).get_session_in_space(space.id, chat_session.id) is None
    assert ChatRepository(session).list_messages(chat_session.id) == []
    assert TraceRepository(session).get_by_trace_id(response.trace_id) is None


def test_chat_service_clear_sessions_removes_all_histories(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    user = UserRepository(session).create(username="dev-user", display_name="Developer")
    space = SpaceRepository(session).create(user_id=user.id, name="Default", slug="default", is_default=True)
    session.flush()
    document = DocumentRepository(session).create(
        space_id=space.id,
        original_filename="demo.pdf",
        normalized_filename="document.pdf",
        file_ext="pdf",
        mime_type="application/pdf",
        source_type=DocumentSourceType.UPLOAD,
        status=DocumentStatus.READY,
        size_bytes=10,
        sha256="b" * 64,
        total_pages=1,
        storage_original_path="orig",
        storage_pdf_path="pdf",
        storage_thumbnail_path=None,
        created_by_user_id=user.id,
    )
    DocumentRepository(session).add_page(
        document_id=document.id,
        space_id=space.id,
        page_no=1,
        width=100,
        height=100,
        storage_image_path="missing.png",
        storage_thumbnail_path=None,
        extracted_text="Paris is the capital of France.",
        extracted_text_source=ExtractedTextSource.NATIVE,
        checksum="c",
    )
    session.commit()

    settings = Settings(
        sqlite_path=str(tmp_path / "app.db"),
        filesystem_storage_root=str(tmp_path / "data"),
        nano_vector_path=str(tmp_path / "vectors"),
        embedding_api_base="",
    )
    storage = StorageService(FilesystemObjectStore(tmp_path / "data"))
    retrieval_service = RetrievalService(
        session,
        NanoVectorStore(tmp_path / "vectors"),
        FakeRerankerClient(),
        FakeEmbeddingClient(),
        settings,
    )
    chat_service = ChatService(
        session,
        settings=settings,
        retrieval_service=retrieval_service,
        llm_client=FakeLLMClient(),
        storage=storage,
    )
    context = CurrentUserContext(user_id=user.id, space_id=space.id, username=user.username, display_name=user.display_name)

    first_session = chat_service.create_session(context, selected_document_ids=[document.id])
    second_session = chat_service.create_session(context, selected_document_ids=[document.id])
    first_response = chat_service.post_message(
        context,
        first_session.id,
        ChatRequest(
            message="First conversation",
            selected_document_ids=[document.id],
            retrieval_config=RetrievalConfig(),
        ),
    )
    second_response = chat_service.post_message(
        context,
        second_session.id,
        ChatRequest(
            message="Second conversation",
            selected_document_ids=[document.id],
            retrieval_config=RetrievalConfig(),
        ),
    )

    deleted_count = chat_service.clear_sessions(context)

    assert deleted_count == 2
    assert chat_service.list_recent_sessions(context) == []
    assert TraceRepository(session).get_by_trace_id(first_response.trace_id) is None
    assert TraceRepository(session).get_by_trace_id(second_response.trace_id) is None


def test_stream_chat_flow_persists_assistant_message_and_trace(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    user = UserRepository(session).create(username="dev-user", display_name="Developer")
    space = SpaceRepository(session).create(user_id=user.id, name="Default", slug="default", is_default=True)
    session.flush()
    document = DocumentRepository(session).create(
        space_id=space.id,
        original_filename="demo.pdf",
        normalized_filename="document.pdf",
        file_ext="pdf",
        mime_type="application/pdf",
        source_type=DocumentSourceType.UPLOAD,
        status=DocumentStatus.READY,
        size_bytes=10,
        sha256="b" * 64,
        total_pages=1,
        storage_original_path="orig",
        storage_pdf_path="pdf",
        storage_thumbnail_path=None,
        created_by_user_id=user.id,
    )
    DocumentRepository(session).add_page(
        document_id=document.id,
        space_id=space.id,
        page_no=1,
        width=100,
        height=100,
        storage_image_path="missing.png",
        storage_thumbnail_path=None,
        extracted_text="The capital of France is Paris.",
        extracted_text_source=ExtractedTextSource.NATIVE,
        checksum="c",
    )
    session.commit()

    settings = Settings(
        sqlite_path=str(tmp_path / "app.db"),
        filesystem_storage_root=str(tmp_path / "data"),
        nano_vector_path=str(tmp_path / "vectors"),
        embedding_api_base="",
    )
    storage = StorageService(FilesystemObjectStore(tmp_path / "data"))
    retrieval_service = RetrievalService(
        session,
        NanoVectorStore(tmp_path / "vectors"),
        FakeRerankerClient(),
        FakeEmbeddingClient(),
        settings,
    )
    llm_client = FakeLLMClient()
    chat_service = ChatService(
        session,
        settings=settings,
        retrieval_service=retrieval_service,
        llm_client=llm_client,
        storage=storage,
    )
    context = CurrentUserContext(user_id=user.id, space_id=space.id, username=user.username, display_name=user.display_name)
    chat_session = chat_service.create_session(context, selected_document_ids=[document.id])
    prepared = chat_service.prepare_stream_message(
        context,
        chat_session.id,
        ChatRequest(
            message="What is the capital of France?",
            selected_document_ids=[document.id],
            retrieval_config=RetrievalConfig(),
        ),
    )

    events = list(chat_service.stream_message(context, chat_session.id, prepared.user_message_id))

    assert [event.event for event in events] == ["status", "meta", "status", "chunk", "status", "done"]
    assert "What is the capital of France?" in llm_client.streamed_messages[-1].content
    messages = ChatRepository(session).list_messages(chat_session.id)
    assert len(messages) == 2
    assert any(message.role == ChatRole.ASSISTANT for message in messages)
    trace_id = events[-1].data["trace_id"]
    trace = TraceRepository(session).get_by_trace_id(trace_id)
    assert trace is not None
