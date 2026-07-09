"""SQLAlchemy-backed Repo + session store for the Postgres deployment.

Each method opens a short-lived session. Complexity notes match the acceptance
criteria: due-fetch is O(log n + k) via idx_due, mastery lookup O(log n), etc.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.agent.state import AgentState
from app.llm.provider import ConceptRef, keywords_of
from app.memory.srs import SRSState


class SqlRepo:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def topic_edges(self, topic: str) -> dict[str, list[str]]:
        """Adjacency {concept: [prereqs]} in one query — no N+1. O(V + E)."""
        with Session(self._engine) as s:
            concepts = s.execute(
                text("SELECT id FROM concepts WHERE topic = :t"), {"t": topic}
            ).scalars()
            edges: dict[str, list[str]] = {cid: [] for cid in concepts}
            rows = s.execute(
                text(
                    "SELECT e.concept_id, e.prereq_id FROM concept_edges e "
                    "JOIN concepts c ON c.id = e.concept_id WHERE c.topic = :t"
                ),
                {"t": topic},
            )
            for concept_id, prereq_id in rows:
                edges.setdefault(concept_id, []).append(prereq_id)
            return edges

    def concept(self, concept_id: str) -> ConceptRef:
        with Session(self._engine) as s:
            row = s.execute(
                text("SELECT id, name, summary FROM concepts WHERE id = :id"),
                {"id": concept_id},
            ).one()
            summary = row.summary or ""
            return ConceptRef(row.id, row.name, summary, keywords_of(summary))

    def learned(self, user_id: str, topic: str) -> set[str]:
        with Session(self._engine) as s:
            rows = s.execute(
                text(
                    "SELECT m.concept_id FROM mastery m JOIN concepts c ON c.id = m.concept_id "
                    "WHERE m.user_id = :u AND c.topic = :t AND m.repetitions >= 1"
                ),
                {"u": user_id, "t": topic},
            ).scalars()
            return set(rows)

    def due(self, user_id: str, now: datetime, limit: int = 10) -> list[str]:
        # O(log n + k): idx_due (user_id, next_review) + LIMIT. Never a full scan.
        with Session(self._engine) as s:
            rows = s.execute(
                text(
                    "SELECT concept_id FROM mastery "
                    "WHERE user_id = :u AND next_review IS NOT NULL AND next_review <= :now "
                    "ORDER BY next_review ASC LIMIT :k"
                ),
                {"u": user_id, "now": now, "k": limit},
            ).scalars()
            return list(rows)

    def mastery(self, user_id: str, concept_id: str) -> SRSState:
        with Session(self._engine) as s:
            row = s.execute(
                text(
                    "SELECT easiness_factor, interval_days, repetitions, next_review, "
                    "mastery_level, last_score FROM mastery "
                    "WHERE user_id = :u AND concept_id = :c"
                ),
                {"u": user_id, "c": concept_id},
            ).one_or_none()
            if row is None:
                return SRSState()
            return SRSState(
                easiness_factor=row.easiness_factor,
                interval_days=row.interval_days,
                repetitions=row.repetitions,
                mastery_level=row.mastery_level,
                last_score=row.last_score,
                next_review=row.next_review,
            )

    def save_mastery(self, user_id: str, concept_id: str, state: SRSState) -> None:
        with Session(self._engine) as s, s.begin():
            s.execute(
                text(
                    "INSERT INTO mastery (user_id, concept_id, easiness_factor, interval_days, "
                    "repetitions, next_review, mastery_level, last_score) "
                    "VALUES (:u, :c, :ef, :iv, :rep, :nr, :ml, :ls) "
                    "ON CONFLICT (user_id, concept_id) DO UPDATE SET "
                    "easiness_factor = :ef, interval_days = :iv, repetitions = :rep, "
                    "next_review = :nr, mastery_level = :ml, last_score = :ls"
                ),
                {
                    "u": user_id,
                    "c": concept_id,
                    "ef": state.easiness_factor,
                    "iv": state.interval_days,
                    "rep": state.repetitions,
                    "nr": state.next_review,
                    "ml": state.mastery_level,
                    "ls": state.last_score,
                },
            )

    def record_attempt(
        self,
        user_id: str,
        concept_id: str,
        question: str,
        answer: str,
        quality: int,
        misconception: str,
    ) -> None:
        with Session(self._engine) as s, s.begin():
            s.execute(
                text(
                    "INSERT INTO quiz_attempts "
                    "(user_id, concept_id, question, user_answer, quality_score, misconception) "
                    "VALUES (:u, :c, :q, :a, :qs, :m)"
                ),
                {"u": user_id, "c": concept_id, "q": question, "a": answer,
                 "qs": quality, "m": misconception},
            )

    # --- read helpers (dashboard / progress) ---
    def concepts(self, topic: str) -> list[ConceptRef]:
        with Session(self._engine) as s:
            rows = s.execute(
                text("SELECT id, name, summary FROM concepts WHERE topic = :t ORDER BY difficulty"),
                {"t": topic},
            )
            return [
                ConceptRef(r.id, r.name, r.summary or "", keywords_of(r.summary or ""))
                for r in rows
            ]

    def attempt_history(
        self, user_id: str, limit: int, offset: int
    ) -> list[dict[str, object]]:
        """Paginated attempts, newest first. O(log n + page) via idx_attempts."""
        with Session(self._engine) as s:
            rows = s.execute(
                text(
                    "SELECT concept_id, question, user_answer, quality_score, misconception, "
                    "created_at FROM quiz_attempts WHERE user_id = :u "
                    "ORDER BY created_at DESC LIMIT :lim OFFSET :off"
                ),
                {"u": user_id, "lim": limit, "off": offset},
            )
            return [
                {
                    "concept_id": r.concept_id,
                    "question": r.question,
                    "answer": r.user_answer,
                    "quality_score": r.quality_score,
                    "misconception": r.misconception,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]


class SqlSessionStore:
    """Persists the bounded AgentState in the sessions table (JSONB `state`),
    mirroring key fields to columns for the dashboard queries.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def ensure_user(self, user_id: str, level: str) -> None:
        with Session(self._engine) as s, s.begin():
            s.execute(
                text(
                    "INSERT INTO users (id, explain_level) VALUES (:id, :lvl) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": user_id, "lvl": level},
            )

    def create(self, session_id: str, state: AgentState) -> None:
        with Session(self._engine) as s, s.begin():
            s.execute(
                text(
                    "INSERT INTO sessions (id, user_id, topic, explain_level, state) "
                    "VALUES (:id, :u, :t, :lvl, CAST(:st AS JSONB))"
                ),
                {
                    "id": session_id,
                    "u": state["user_id"],
                    "t": state["topic"],
                    "lvl": state["explain_level"],
                    "st": _dumps(state),
                },
            )

    def get(self, session_id: str) -> AgentState | None:
        with Session(self._engine) as s:
            row = s.execute(
                text("SELECT state FROM sessions WHERE id = :id"), {"id": session_id}
            ).one_or_none()
            if row is None:
                return None
            return cast(AgentState, dict(row.state))

    def put(self, session_id: str, state: AgentState) -> None:
        with Session(self._engine) as s, s.begin():
            s.execute(
                text(
                    "UPDATE sessions SET state = CAST(:st AS JSONB), "
                    "path = CAST(:path AS JSONB), current_concept = :cc, "
                    "running_summary = :rs, phase = :ph, updated_at = now() WHERE id = :id"
                ),
                {
                    "id": session_id,
                    "st": _dumps(state),
                    "path": _dumps(state.get("path", [])),
                    "cc": state.get("current_concept"),
                    "rs": state.get("running_summary", ""),
                    "ph": state.get("phase", "teach"),
                },
            )


def _dumps(obj: object) -> str:
    import json

    return json.dumps(obj, default=str)
