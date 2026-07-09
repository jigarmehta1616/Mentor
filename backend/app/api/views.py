"""Turn a bounded AgentState into a client-facing view."""

from __future__ import annotations

from typing import Any

from app.agent.state import AgentState
from app.api.engine import Engine


def turn_view(engine: Engine, session_id: str, state: AgentState) -> dict[str, Any]:
    concept_id = state.get("current_concept")
    concept: dict[str, str] | None = None
    if concept_id:
        ref = engine.repo.concept(concept_id)
        concept = {"id": ref.id, "name": ref.name}
    return {
        "session_id": session_id,
        "phase": state.get("phase", "teach"),
        "done": state.get("phase") == "done",
        "current_concept": concept,
        "explanation": state.get("last_explanation"),
        "question": state.get("last_quiz"),
        "citations": state.get("citations", []),
        "grade": state.get("last_grade"),
        "diagnosis": state.get("diagnosis"),
        "due": state.get("due", []),
    }
