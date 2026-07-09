"""diagnoser node: identify the specific misconception behind a wrong answer."""

from __future__ import annotations

from collections.abc import Callable

from app.agent.deps import Deps
from app.agent.state import AgentState
from app.llm.provider import GradeResult


def make_diagnoser(deps: Deps) -> Callable[[AgentState], dict[str, object]]:
    def diagnoser(state: AgentState) -> dict[str, object]:
        concept = deps.repo.concept(state["current_concept"])  # type: ignore[arg-type]
        grade = state["last_grade"] or {}
        result = deps.provider.diagnose(
            concept,
            state.get("last_quiz") or "",
            "",  # the answer was already folded into the window/attempt
            GradeResult(int(grade.get("quality", 0)), str(grade.get("misconception", "")), ""),
        )
        return {
            "diagnosis": {
                "misconception": result.misconception,
                "subpoint": result.subpoint,
                "remediation": result.remediation,
            }
        }

    return diagnoser
