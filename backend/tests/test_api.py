"""End-to-end API tests against the in-memory backend (no DB, no keys)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    os.environ["DATABASE_URL"] = "memory://"
    os.environ["LLM_PROVIDER"] = "mock"
    # Reset cached singletons so the memory backend is picked up.
    from app.api import engine as engine_mod
    from app.config import get_settings
    from app.llm import provider as provider_mod

    get_settings.cache_clear()
    provider_mod.get_provider.cache_clear()
    engine_mod.get_engine.cache_clear()

    from app.main import create_app

    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["provider"] == "mock"


def test_full_learning_loop(client: TestClient) -> None:
    start = client.post(
        "/sessions", json={"user_id": "learner", "topic": "sql", "level": "student"}
    ).json()
    sid = start["session_id"]
    first_concept = start["current_concept"]["id"]
    assert start["question"]
    assert start["citations"]
    assert start["phase"] == "quiz"

    # Wrong answer → targeted re-teach, same concept.
    r = client.post(f"/sessions/{sid}/turn", json={"answer": "no idea"})
    assert r.status_code == 200
    text = r.text
    assert "event: grade" in text and "event: done" in text
    assert "focus on" in text  # re-teaches the diagnosed sub-point

    # Correct answer → advance + schedule review.
    concept = client.get("/paths/learner", params={"topic": "sql"}).json()
    good = next(c for c in concept["path"] if c["id"] == first_concept)["name"]
    answer = good + " relational tables rows keys"
    r2 = client.post(f"/sessions/{sid}/turn", json={"answer": answer})
    assert r2.status_code == 200

    progress = client.get(
        "/progress/learner", params={"topic": "sql", "limit": 5}
    ).json()
    assert len(progress["mastery"]) > 0
    assert len(progress["history"]) >= 2  # two attempts recorded
    assert progress["page"]["limit"] == 5


def test_turn_on_missing_session_404(client: TestClient) -> None:
    r = client.post("/sessions/does-not-exist/turn", json={"answer": "x"})
    assert r.status_code == 404


def test_paths_and_reviews_shape(client: TestClient) -> None:
    client.post("/sessions", json={"user_id": "u2", "topic": "sql", "level": "expert"})
    path = client.get("/paths/u2", params={"topic": "sql"}).json()
    assert path["topic"] == "sql"
    assert all("status" in item for item in path["path"])
    reviews = client.get("/reviews/u2").json()
    assert reviews["user_id"] == "u2"
    assert isinstance(reviews["due"], list)
