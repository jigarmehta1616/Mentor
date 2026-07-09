"""Repository protocol the agent nodes depend on.

Decouples the graph from persistence: the API wires a SQLAlchemy-backed repo,
tests wire an in-memory one. All hot-path methods document their complexity.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.llm.provider import ConceptRef
from app.memory.srs import SRSState


class Repo(Protocol):
    def topic_edges(self, topic: str) -> dict[str, list[str]]:
        """Adjacency map {concept_id: [prereq_ids]} for a topic. O(V + E)."""
        ...

    def concept(self, concept_id: str) -> ConceptRef:
        """Fetch one concept. O(log n) (primary key)."""
        ...

    def learned(self, user_id: str, topic: str) -> set[str]:
        """Concept ids the user has passed at least once (SM-2 repetitions >= 1)."""
        ...

    def due(self, user_id: str, now: datetime, limit: int = 10) -> list[str]:
        """Concept ids due for review, soonest first. O(log n + k) via idx_due."""
        ...

    def mastery(self, user_id: str, concept_id: str) -> SRSState:
        """Current SM-2 state for (user, concept). O(log n)."""
        ...

    def save_mastery(self, user_id: str, concept_id: str, state: SRSState) -> None:
        """Upsert SM-2 state. O(log n)."""
        ...

    def record_attempt(
        self,
        user_id: str,
        concept_id: str,
        question: str,
        answer: str,
        quality: int,
        misconception: str,
    ) -> None:
        """Append a quiz attempt. O(1) amortized (indexed append)."""
        ...
