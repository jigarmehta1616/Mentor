"""Typed, bounded agent state for the LangGraph machine.

The state is deliberately small and JSON-serializable. ``window`` is capped at
the last W turns; older turns are folded into ``running_summary`` so the token
cost of an LLM call is O(W), constant in session length.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.config import ExplainLevel
from app.memory.context import Turn, roll


class AgentState(TypedDict, total=False):
    # identity / config
    user_id: str
    topic: str
    explain_level: ExplainLevel

    # plan
    path: list[str]
    current_concept: str | None

    # bounded conversation
    window: list[dict[str, str]]  # [{role, content}] — capped at W
    running_summary: str

    # per-turn I/O
    answer: str | None
    last_quiz: str | None
    last_explanation: str | None
    citations: list[dict[str, str]]
    last_grade: dict[str, Any] | None
    diagnosis: dict[str, str] | None

    # control
    due: list[str]
    reteach: bool
    phase: str  # 'teach' | 'quiz' | 'review' | 'done'


def append_turn(
    state: AgentState, role: str, content: str, window_size: int
) -> None:
    """Append a turn to the bounded window, folding overflow into the summary.

    Amortized O(1): each turn is folded at most once. Mutates ``state`` in place.
    """
    window = [Turn(t["role"], t["content"]) for t in state.get("window", [])]
    result = roll(state.get("running_summary", ""), window, Turn(role, content), window_size)
    state["window"] = [{"role": t.role, "content": t.content} for t in result.window]
    state["running_summary"] = result.summary
