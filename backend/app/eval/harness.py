"""Evaluation harness: does adaptive teaching lift quiz scores vs a static syllabus?

A simulated learner has a per-concept skill level and answers quizzes by
emitting a proportion of the concept's key ideas (so the *real* grader scores
it). Teaching raises skill; a targeted re-teach of a diagnosed gap raises it
more. We run two arms over the same topic:

  * static  — teach each concept once, quiz once, never adapt.
  * adaptive — the full agent: re-teach diagnosed gaps until mastered.

and report the delta in mastery and mean quiz quality.

Run:  python -m app.eval.harness
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from app.agent.deps import Deps
from app.agent.graph import build_graph
from app.agent.memory_repo import InMemoryRepo
from app.agent.state import AgentState
from app.config import ExplainLevel
from app.llm.provider import ConceptRef, MockProvider
from app.memory.graph_utils import topological_sort

BASE_GAIN = 0.20  # skill gained from one explanation
TARGETED_GAIN = 0.38  # extra skill from a targeted re-teach of the diagnosed gap
START_SKILL = 0.12
ATTEMPT_CAP = 4  # max re-teach attempts per concept in the adaptive arm


@dataclass
class SimLearner:
    """A learner with per-concept skill in [0, 1]."""

    skill: dict[str, float] = field(default_factory=dict)

    def answer(self, concept: ConceptRef) -> str:
        """Emit a partial answer: the first ``skill * k`` key ideas."""
        s = self.skill.get(concept.id, START_SKILL)
        kws = concept.keywords
        k = round(s * len(kws))
        return f"{concept.name}: " + " ".join(kws[:k])

    def study(self, concept_id: str, amount: float) -> None:
        self.skill[concept_id] = min(1.0, self.skill.get(concept_id, START_SKILL) + amount)


@dataclass
class ArmResult:
    arm: str
    mastered: int
    total: int
    mean_quality: float
    attempts: int

    @property
    def mastery_rate(self) -> float:
        return self.mastered / self.total if self.total else 0.0


def run_static(topic: str) -> ArmResult:
    """Teach each concept once, quiz once, no adaptation."""
    repo = InMemoryRepo()
    provider = MockProvider()
    learner = SimLearner()
    order = topological_sort(repo.topic_edges(topic))

    qualities: list[int] = []
    for cid in order:
        concept = repo.concept(cid)
        learner.study(cid, BASE_GAIN)  # single explanation
        grade = provider.grade(concept, "", learner.answer(concept))
        qualities.append(grade.quality)

    mastered = sum(1 for q in qualities if q >= 3)
    mean = sum(qualities) / len(qualities) if qualities else 0.0
    return ArmResult("static", mastered, len(order), round(mean, 2), len(qualities))


def run_adaptive(topic: str, level: ExplainLevel = "student") -> ArmResult:
    """Drive the full agent graph; the learner improves on targeted re-teaches."""
    repo = InMemoryRepo()
    provider = MockProvider()
    graph = build_graph(Deps(provider, repo, window_size=8))
    learner = SimLearner()

    order = topological_sort(repo.topic_edges(topic))
    state: AgentState = AgentState(
        user_id="sim", topic=topic, explain_level=level,
        window=[], running_summary="", answer=None, reteach=False,
    )
    state = cast(AgentState, dict(graph.invoke(state)))
    taught = state.get("current_concept")
    if taught:
        learner.study(taught, BASE_GAIN)

    best: dict[str, int] = {}
    attempts = 0
    steps = 0
    per_concept_tries: dict[str, int] = {}
    while not state.get("phase") == "done" and state.get("current_concept") and steps < 60:
        steps += 1
        cid = state["current_concept"]
        assert cid is not None
        per_concept_tries[cid] = per_concept_tries.get(cid, 0) + 1
        concept = repo.concept(cid)

        state["answer"] = learner.answer(concept)
        state = cast(AgentState, dict(graph.invoke(state)))
        attempts += 1
        grade = state.get("last_grade") or {}
        q = int(grade.get("quality", 0))
        best[cid] = max(best.get(cid, 0), q)

        new_cid = state.get("current_concept")
        if state.get("diagnosis") and new_cid == cid:
            if per_concept_tries[cid] >= ATTEMPT_CAP:
                # Give up on this concept to avoid an infinite remediation loop.
                learner.study(cid, 1.0)
            else:
                learner.study(cid, TARGETED_GAIN)  # remediation of the diagnosed gap
        elif new_cid and new_cid != cid and new_cid not in learner.skill:
            learner.study(new_cid, BASE_GAIN)  # advanced: next concept just taught

    total = len(order)
    mastered = sum(1 for cid in order if best.get(cid, 0) >= 3)
    mean = sum(best.get(cid, 0) for cid in order) / total if total else 0.0
    return ArmResult("adaptive", mastered, total, round(mean, 2), attempts)


def evaluate(topic: str = "neural-networks") -> dict[str, ArmResult]:
    return {"static": run_static(topic), "adaptive": run_adaptive(topic)}


def _format(results: dict[str, ArmResult]) -> str:
    s, a = results["static"], results["adaptive"]
    lift = round((a.mastery_rate - s.mastery_rate) * 100, 1)
    def row(r: ArmResult) -> str:
        return (
            f"{r.arm:<9} {r.mastered}/{r.total} ({r.mastery_rate:.0%})   "
            f"{r.mean_quality:<12} {r.attempts}"
        )

    lines = [
        "arm       mastery   mean_quality   quiz_attempts",
        row(s),
        row(a),
        f"\nAdaptive lifts mastery by {lift:+} percentage points "
        f"({s.mean_quality} -> {a.mean_quality} mean quiz quality).",
    ]
    return "\n".join(lines)


def main() -> None:
    for topic in ("neural-networks", "sql"):
        print(f"\n=== Topic: {topic} ===")
        print(_format(evaluate(topic)))


if __name__ == "__main__":
    main()
