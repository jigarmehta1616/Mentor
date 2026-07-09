"""In-memory Repo implementation backed by the seed DAGs.

Used by tests and the evaluation harness; lets the whole agent run with no
database. The SQLAlchemy-backed repo used by the API lives in the API layer.
"""

from __future__ import annotations

from datetime import datetime

from app.agent.repo import Repo
from app.llm.provider import ConceptRef, keywords_of
from app.memory.srs import SRSState
from app.seed.concepts import TOPICS, SeedConcept, edges_for_topic


def _to_ref(c: SeedConcept) -> ConceptRef:
    return ConceptRef(id=c.id, name=c.name, summary=c.summary, keywords=keywords_of(c.summary))


class InMemoryRepo(Repo):
    def __init__(self) -> None:
        self._concepts: dict[str, ConceptRef] = {
            c.id: _to_ref(c) for concepts in TOPICS.values() for c in concepts
        }
        self._topic_of: dict[str, str] = {
            c.id: topic for topic, concepts in TOPICS.items() for c in concepts
        }
        self._mastery: dict[tuple[str, str], SRSState] = {}
        self.attempts: list[dict[str, object]] = []

    def topic_edges(self, topic: str) -> dict[str, list[str]]:
        return edges_for_topic(topic)

    def concept(self, concept_id: str) -> ConceptRef:
        return self._concepts[concept_id]

    def learned(self, user_id: str, topic: str) -> set[str]:
        return {
            cid
            for (uid, cid), st in self._mastery.items()
            if uid == user_id and self._topic_of.get(cid) == topic and st.repetitions >= 1
        }

    def due(self, user_id: str, now: datetime, limit: int = 10) -> list[str]:
        rows = [
            (st.next_review, cid)
            for (uid, cid), st in self._mastery.items()
            if uid == user_id and st.next_review is not None and st.next_review <= now
        ]
        rows.sort(key=lambda r: r[0])
        return [cid for _, cid in rows[:limit]]

    def mastery(self, user_id: str, concept_id: str) -> SRSState:
        return self._mastery.get((user_id, concept_id), SRSState())

    def save_mastery(self, user_id: str, concept_id: str, state: SRSState) -> None:
        self._mastery[(user_id, concept_id)] = state

    def record_attempt(
        self,
        user_id: str,
        concept_id: str,
        question: str,
        answer: str,
        quality: int,
        misconception: str,
    ) -> None:
        self.attempts.append(
            {
                "user_id": user_id,
                "concept_id": concept_id,
                "question": question,
                "answer": answer,
                "quality_score": quality,
                "misconception": misconception,
            }
        )

    # --- read helpers (dashboard / progress) ---
    def concepts(self, topic: str) -> list[ConceptRef]:
        return [_to_ref(c) for c in TOPICS.get(topic, [])]

    def attempt_history(
        self, user_id: str, limit: int, offset: int
    ) -> list[dict[str, object]]:
        """Most-recent-first page of this user's attempts. O(n) in-memory."""
        mine = [a for a in self.attempts if a["user_id"] == user_id]
        return list(reversed(mine))[offset : offset + limit]
