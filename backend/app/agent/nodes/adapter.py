"""adapter node: apply the SM-2 update and decide re-teach vs advance.

The scheduling math is deterministic (memory/srs.py) — the LLM only graded and
diagnosed. q >= 3 advances to the next concept; q < 3 keeps the concept and
flags a targeted re-teach of the diagnosed gap.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.agent.deps import Deps
from app.agent.state import AgentState
from app.memory.srs import PASS_THRESHOLD, update


def make_adapter(deps: Deps) -> Callable[[AgentState], dict[str, object]]:
    def adapter(state: AgentState) -> dict[str, object]:
        concept_id = state["current_concept"]
        assert concept_id is not None
        grade = state["last_grade"] or {}
        quality = int(grade.get("quality", 0))

        # Deterministic SM-2 update + next_review write — O(1).
        prev = deps.repo.mastery(state["user_id"], concept_id)
        new = update(prev, quality, datetime.now(UTC))
        deps.repo.save_mastery(state["user_id"], concept_id, new)

        if quality >= PASS_THRESHOLD:
            # Advance: clear the concept so the planner picks the next one.
            return {"current_concept": None, "reteach": False, "diagnosis": None, "phase": "teach"}
        # Re-teach the same concept, targeting the diagnosed sub-point.
        return {"reteach": True, "phase": "teach"}

    return adapter
