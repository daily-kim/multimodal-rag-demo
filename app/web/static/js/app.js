function autoSizeComposer(textarea) {
  textarea.style.height = "0px";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 280)}px`;
}

function scrollChatToBottom() {
  const threadWrap = document.querySelector(".chat-thread-wrap");
  if (threadWrap) {
    threadWrap.scrollTop = threadWrap.scrollHeight;
  }
}

function refreshChatUI(options = {}) {
  if (options.scroll) {
    scrollChatToBottom();
  }
  document.querySelectorAll("[data-autosize]").forEach((textarea) => autoSizeComposer(textarea));
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function ensureThread() {
  const thread = document.querySelector(".chat-thread");
  if (!thread) {
    return null;
  }
  const empty = thread.querySelector(".chat-empty-state");
  if (empty) {
    empty.remove();
  }
  return thread;
}

function formatBubbleContent(role, content) {
  const escaped = escapeHtml(content);
  if (role === "assistant") {
    return escaped.replaceAll("\n", "<br>");
  }
  return escaped;
}

function buildMessageMarkup(role, content, options = {}) {
  const label = role === "user" ? "You" : role === "assistant" ? "Assistant" : "System";
  const avatar = role === "user" ? "ME" : role === "assistant" ? "AI" : "SYS";
  const traceHtml = options.traceId
    ? `<code class="trace-chip" title="${escapeHtml(options.traceId)}">${escapeHtml(`${options.traceId.slice(0, 12)}...`)}</code>`
    : "";
  const streamingClass = options.streaming ? " is-streaming" : "";
  const statusHtml = options.streaming
    ? `<div class="chat-stream-status">${escapeHtml(options.status || "Preparing an answer...")}</div>`
    : "";
  const bubbleClass = role === "assistant" ? "chat-bubble chat-rich" : "chat-bubble";
  return `
    <article class="chat-message role-${role}${streamingClass}">
      <div class="chat-avatar">${avatar}</div>
      <div class="chat-card">
        <header class="chat-message-head">
          <strong>${label}</strong>
          ${traceHtml}
        </header>
        ${statusHtml}
        <div class="${bubbleClass}">${formatBubbleContent(role, content)}</div>
      </div>
    </article>
  `;
}

function appendMessage(role, content, options = {}) {
  const thread = ensureThread();
  if (!thread) {
    return null;
  }
  thread.insertAdjacentHTML("beforeend", buildMessageMarkup(role, content, options));
  const message = thread.lastElementChild;
  scrollChatToBottom();
  return message;
}

function setStreamingState(form, isStreaming) {
  form.dataset.streaming = isStreaming ? "true" : "false";
  const button = form.querySelector(".compose-submit");
  const label = button?.querySelector(".button-label");
  if (button) {
    button.disabled = isStreaming;
  }
  if (label) {
    label.textContent = isStreaming ? "Generating..." : "Send prompt";
  }
}

async function replaceChatPanel(panelUrl, traceId) {
  const url = traceId ? `${panelUrl}?trace_id=${encodeURIComponent(traceId)}` : panelUrl;
  const response = await fetch(url, {
    headers: { "HX-Request": "true" },
    credentials: "same-origin",
  });
  if (!response.ok) {
    throw new Error("chat panel refresh failed");
  }
  const html = await response.text();
  const existing = document.querySelector("#chat-panel");
  if (!existing) {
    return;
  }
  existing.outerHTML = html;
  refreshChatUI({ scroll: true });
}

const activeStreams = new Map();

async function submitStreamingForm(form) {
  if (form.dataset.streaming === "true") {
    return;
  }

  const textarea = form.querySelector(".composer-textarea");
  const message = textarea?.value.trim() || "";
  if (!message) {
    textarea?.focus();
    return;
  }

  const initUrl = form.dataset.streamInitUrl;
  const panelUrl = form.dataset.panelUrl;
  const sessionId = form.dataset.sessionId;
  if (!initUrl || !panelUrl || !sessionId) {
    return;
  }

  setStreamingState(form, true);

  try {
    const formData = new FormData(form);
    const initResponse = await fetch(initUrl, {
      method: "POST",
      body: formData,
      credentials: "same-origin",
    });
    if (!initResponse.ok) {
      throw new Error("stream init failed");
    }
    const initPayload = await initResponse.json();

    appendMessage("user", message);
    const assistantMessage = appendMessage("assistant", "", {
      streaming: true,
      status: "Finding relevant pages and evidence...",
    });
    const assistantBubble = assistantMessage?.querySelector(".chat-bubble");
    const assistantStatus = assistantMessage?.querySelector(".chat-stream-status");

    if (textarea) {
      textarea.value = "";
      autoSizeComposer(textarea);
      textarea.focus();
    }

    const currentSource = activeStreams.get(sessionId);
    if (currentSource) {
      currentSource.close();
    }

    const source = new EventSource(initPayload.stream_url);
    activeStreams.set(sessionId, source);
    let answer = "";
    let completed = false;

    source.addEventListener("chunk", (event) => {
      const data = JSON.parse(event.data);
      answer += data.text || "";
      if (assistantBubble) {
        assistantBubble.innerHTML = formatBubbleContent("assistant", answer || " ");
      }
      if (assistantStatus) {
        assistantStatus.textContent = "Generating answer...";
      }
      scrollChatToBottom();
    });

    source.addEventListener("status", (event) => {
      const data = JSON.parse(event.data);
      if (assistantStatus) {
        assistantStatus.textContent = data.label || "Generating answer...";
      }
    });

    source.addEventListener("done", async (event) => {
      const data = JSON.parse(event.data);
      completed = true;
      source.close();
      activeStreams.delete(sessionId);
      try {
        await replaceChatPanel(panelUrl, data.trace_id);
      } finally {
        const nextForm = document.querySelector("#chat-form");
        if (nextForm) {
          setStreamingState(nextForm, false);
          nextForm.querySelector(".composer-textarea")?.focus();
        }
      }
    });

    source.addEventListener("chat_error", (event) => {
      completed = true;
      const data = JSON.parse(event.data);
      source.close();
      activeStreams.delete(sessionId);
      if (assistantStatus) {
        assistantStatus.textContent = "Error";
      }
      if (assistantBubble) {
        assistantBubble.textContent = data.message || "An error occurred while generating the answer.";
      }
      const nextForm = document.querySelector("#chat-form");
      if (nextForm) {
        setStreamingState(nextForm, false);
      }
    });

    source.onerror = () => {
      if (completed) {
        return;
      }
      source.close();
      activeStreams.delete(sessionId);
      if (assistantStatus) {
        assistantStatus.textContent = "Connection closed";
      }
      if (assistantBubble && !answer) {
        assistantBubble.textContent = "The streaming connection was interrupted. Please try again.";
      }
      const nextForm = document.querySelector("#chat-form");
      if (nextForm) {
        setStreamingState(nextForm, false);
      }
    };
  } catch (error) {
    const thread = ensureThread();
    if (thread) {
      appendMessage("system", "Could not start the request. Please try again in a moment.");
    }
    setStreamingState(form, false);
  }
}

window.refreshChatUI = refreshChatUI;

document.addEventListener("DOMContentLoaded", () => refreshChatUI({ scroll: true }));
document.addEventListener("htmx:afterSwap", (event) => {
  const target = event.detail?.target;
  const shouldScroll = Boolean(target && (target.id === "chat-panel" || target.closest?.("#chat-panel")));
  refreshChatUI({ scroll: shouldScroll && target?.id === "chat-panel" });
});

document.addEventListener("input", (event) => {
  if (event.target.matches("[data-autosize]")) {
    autoSizeComposer(event.target);
  }
});

document.addEventListener(
  "submit",
  (event) => {
    const form = event.target;
    if (!form.matches(".chat-compose-form") || !window.EventSource) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    submitStreamingForm(form);
  },
  true,
);

document.addEventListener("keydown", (event) => {
  if (!event.target.matches(".composer-textarea")) {
    return;
  }

  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    event.target.form?.requestSubmit();
  }
});
