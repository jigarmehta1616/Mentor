"""scheduler node: at session start, surface due reviews before new material."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.agent.deps import Deps
from app.agent.state import AgentState


def make_scheduler(deps: Deps) -> Callable[[AgentState], dict[str, object]]:
    def scheduler(state: AgentState) -> dict[str, object]:
        # O(log n + k): indexed due-query, not a full scan.
        due = deps.repo.due(state["user_id"], datetime.now(UTC))
        out: dict[str, object] = {"due": due}
        # If a review is due and we haven't picked a concept yet, review it first.
        if due and not state.get("current_concept"):
            out["current_concept"] = due[0]
            out["phase"] = "review"
        return out

    return scheduler
