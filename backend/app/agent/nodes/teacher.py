"""teacher node: explain the current concept at the chosen level, with citations.

On a re-teach (after a wrong answer) it targets the diagnosed sub-point rather
than repeating the same explanation.
"""

from __future__ import annotations

from collections.abc import Callable

from app.agent.deps import Deps
from app.agent.state import AgentState, append_turn
from app.agent.tools import web_search
from app.llm.provider import ConceptRef


def make_teacher(deps: Deps) -> Callable[[AgentState], dict[str, object]]:
    def teacher(state: AgentState) -> dict[str, object]:
        concept_id = state.get("current_concept")
        if not concept_id:
            return {"phase": "done"}

        concept = deps.repo.concept(concept_id)
        resources = web_search.search(concept.id, concept.name)  # O(1) amortized (cached)

        target = concept
        diagnosis = state.get("diagnosis")
        if state.get("reteach") and diagnosis:
            # Re-teach the specific misunderstood sub-point, not the whole concept.
            target = ConceptRef(
                id=concept.id,
                name=f"{concept.name} — focus on {diagnosis['subpoint']}",
                summary=diagnosis.get("remediation", concept.summary),
                keywords=concept.keywords,
            )

        text = deps.provider.teach(target, state["explain_level"], resources)
        append_turn(state, "assistant", text, deps.window_size)
        return {
            "last_explanation": text,
            "citations": [{"title": r.title, "url": r.url} for r in resources],
            "window": state["window"],
            "running_summary": state["running_summary"],
        }

    return teacher
