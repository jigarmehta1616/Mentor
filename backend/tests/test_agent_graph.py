"""Integration test: the agent graph drives teach → quiz → grade → adapt with
the mock provider and in-memory repo (no DB, no keys)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.agent.deps import Deps
from app.agent.graph import build_graph
from app.agent.memory_repo import InMemoryRepo
from app.agent.state import AgentState
from app.llm.provider import MockProvider


def _fresh() -> tuple[object, InMemoryRepo]:
    repo = InMemoryRepo()
    deps = Deps(provider=MockProvider(), repo=repo, window_size=4)
    return build_graph(deps), repo


def _base_state() -> AgentState:
    return AgentState(
        user_id="u1",
        topic="neural-networks",
        explain_level="student",
        window=[],
        running_summary="",
        answer=None,
        reteach=False,
    )


def test_present_turn_teaches_and_quizzes() -> None:
    graph, _ = _fresh()
    out = graph.invoke(_base_state())
    assert out["path"], "planner built a topological path"
    assert out["current_concept"] == out["path"][0], "starts at the first concept"
    assert out["last_explanation"]
    assert out["last_quiz"]
    assert out["citations"], "teacher attached cited resources"
    assert out["phase"] == "quiz"


def test_wrong_answer_triggers_targeted_reteach_same_concept() -> None:
    graph, _ = _fresh()
    presented = graph.invoke(_base_state())
    concept = presented["current_concept"]
    first_explanation = presented["last_explanation"]

    # A blank/incorrect answer should grade < 3 and NOT advance.
    state = AgentState(**{**presented, "answer": "i have no idea"})
    graded = graph.invoke(state)

    assert graded["last_grade"]["quality"] < 3
    assert graded["current_concept"] == concept, "stays on the same concept"
    assert graded["last_explanation"] != first_explanation, "re-teaches, doesn't repeat"
    assert "focus on" in graded["last_explanation"], "targets the diagnosed sub-point"


def test_correct_answer_advances_and_schedules_review() -> None:
    graph, repo = _fresh()
    presented = graph.invoke(_base_state())
    concept = presented["current_concept"]
    ref = repo.concept(concept)
    good_answer = f"{ref.name}: " + " ".join(ref.keywords)

    graded = graph.invoke(AgentState(**{**presented, "answer": good_answer}))

    assert graded["last_grade"]["quality"] >= 3
    assert graded["current_concept"] != concept, "advances to the next concept"
    # SM-2 scheduled a future review for the mastered concept.
    assert repo.mastery("u1", concept).next_review is not None
    assert repo.mastery("u1", concept).repetitions >= 1


def test_due_review_surfaces_first_in_a_later_session() -> None:
    graph, repo = _fresh()
    # Make an already-seen concept due now.
    from app.memory.srs import update

    past = datetime(2020, 1, 1, tzinfo=UTC)
    cid = "nn.linear_algebra"
    repo.save_mastery("u1", cid, update(repo.mastery("u1", cid), 4, past))

    out = graph.invoke(_base_state())
    assert "nn.linear_algebra" in out["due"]
    assert out["current_concept"] == "nn.linear_algebra", "reviews the due item first"
    assert out["phase"] == "quiz"
