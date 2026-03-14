from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.domain.schemas.chat import RetrievalConfig
from app.main import render_markdown


def test_chat_panel_renders_evidence_toggle_for_each_assistant_message() -> None:
    templates_dir = Path(__file__).resolve().parents[2] / "app" / "web" / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["markdown"] = render_markdown
    template = env.get_template("partials/chat_panel.html")

    html = template.render(
        request=None,
        current_user=None,
        chat_session=SimpleNamespace(id="session-1"),
        retrieval_defaults=RetrievalConfig(),
        latest_response=None,
        messages=[
            SimpleNamespace(id="m1", role="user", content="Question 1", trace_id=None),
            SimpleNamespace(id="m2", role="assistant", content="Answer 1", trace_id="trace-1"),
            SimpleNamespace(id="m3", role="assistant", content="Answer 2", trace_id="trace-2"),
        ],
    )

    assert "/partials/chat/session-1/evidence/trace-1" in html
    assert "/partials/chat/session-1/evidence/trace-2" in html


def test_chat_message_renders_user_bubble_without_template_whitespace() -> None:
    templates_dir = Path(__file__).resolve().parents[2] / "app" / "web" / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["markdown"] = render_markdown
    template = env.get_template("partials/chat_message.html")

    html = template.render(
        message=SimpleNamespace(id="m1", role="user", content="hi", trace_id=None),
        chat_session=SimpleNamespace(id="session-1"),
    )

    assert '<div class="chat-bubble">hi</div>' in html


def test_chat_page_renders_session_delete_controls() -> None:
    templates_dir = Path(__file__).resolve().parents[2] / "app" / "web" / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["markdown"] = render_markdown
    env.globals["url_for"] = lambda *_args, **kwargs: f"/static/{kwargs.get('path', '')}"
    template = env.get_template("chat.html")

    html = template.render(
        request=None,
        current_user=None,
        documents=[],
        chat_sessions=[
            SimpleNamespace(id="session-1", title="First chat", updated_at=SimpleNamespace(strftime=lambda _: "2026-03-14 18:00")),
            SimpleNamespace(id="session-2", title="Second chat", updated_at=SimpleNamespace(strftime=lambda _: "2026-03-14 18:05")),
        ],
        chat_session=SimpleNamespace(id="session-1"),
        messages=[],
        selected_document_ids=set(),
        retrieval_defaults=RetrievalConfig(),
        latest_response=None,
        page_title="Chat",
    )

    assert "/api/chat/sessions/clear" in html
    assert "/api/chat/sessions/session-1/delete" in html
    assert "/api/chat/sessions/session-2/delete" in html
