"""quizzer node: ask a targeted question about the current concept."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.deps import Deps
from app.agent.state import AgentState, append_turn
from app.agent.tools import quiz_gen


def make_quizzer(deps: Deps) -> Callable[[AgentState], dict[str, object]]:
    def quizzer(state: AgentState) -> dict[str, object]:
        concept_id = state.get("current_concept")
        if not concept_id:
            return {"phase": "done"}
        concept = deps.repo.concept(concept_id)
        question = quiz_gen.generate_question(deps.provider, concept, state["explain_level"])
        append_turn(state, "assistant", question, deps.window_size)
        return {
            "last_quiz": question,
            "phase": "quiz",
            "window": state["window"],
            "running_summary": state["running_summary"],
        }

    return quizzer
