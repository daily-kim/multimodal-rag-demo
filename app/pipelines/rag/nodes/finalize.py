from __future__ import annotations

import time
from typing import Callable

from app.pipelines.rag.state import RagState


def make_finalize_node(persist_result: Callable[[dict], None]):
    def node(state: RagState) -> RagState:
        metrics = dict(state.get("metrics", {}))
        total = sum(metrics.values())
        metrics["latency_ms_total"] = total
        state["metrics"] = metrics
        persist_result(state)
        return {"metrics": metrics}

    return node

