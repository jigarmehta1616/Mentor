"""grader node: score the learner's answer 0..5 (SM-2 quality) and record it."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.deps import Deps
from app.agent.state import AgentState, append_turn


def make_grader(deps: Deps) -> Callable[[AgentState], dict[str, object]]:
    def grader(state: AgentState) -> dict[str, object]:
        concept_id = state["current_concept"]
        answer = state.get("answer") or ""
        question = state.get("last_quiz") or ""
        assert concept_id is not None

        concept = deps.repo.concept(concept_id)
        append_turn(state, "user", answer, deps.window_size)

        result = deps.provider.grade(concept, question, answer)
        deps.repo.record_attempt(
            state["user_id"], concept_id, question, answer, result.quality, result.misconception
        )
        return {
            "last_grade": {
                "quality": result.quality,
                "misconception": result.misconception,
                "feedback": result.feedback,
            },
            "answer": None,  # consume the answer
            "window": state["window"],
            "running_summary": state["running_summary"],
        }

    return grader
