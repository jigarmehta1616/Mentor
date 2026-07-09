"""planner node: build the learning path (topo sort) and pick the next concept."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.deps import Deps
from app.agent.state import AgentState
from app.memory.graph_utils import topological_sort


def make_planner(deps: Deps) -> Callable[[AgentState], dict[str, object]]:
    def planner(state: AgentState) -> dict[str, object]:
        out: dict[str, object] = {}

        # Build the ordered path once (O(V + E), cycle-checked) and reuse it.
        path = state.get("path") or []
        if not path:
            edges = deps.repo.topic_edges(state["topic"])
            path = topological_sort(edges)  # raises CycleError on a bad DAG
            out["path"] = path

        # A due review already chosen by the scheduler takes priority.
        if state.get("current_concept"):
            return out

        # Otherwise advance to the first concept the user hasn't passed yet.
        learned = deps.repo.learned(state["user_id"], state["topic"])
        nxt = next((c for c in path if c not in learned), None)
        out["current_concept"] = nxt
        out["phase"] = "teach" if nxt else "done"
        return out

    return planner
