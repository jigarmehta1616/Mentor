"""Application engine: wires provider + repo + session store + agent graph, and
drives one session step per request.

Backend is chosen by DATABASE_URL: ``memory://`` runs fully in-process (no DB,
handy for the keyless demo and tests); anything else uses Postgres.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Protocol, cast

from app.agent.deps import Deps
from app.agent.graph import build_graph
from app.agent.memory_repo import InMemoryRepo
from app.agent.repo import Repo
from app.agent.state import AgentState
from app.config import ExplainLevel, get_settings
from app.llm.provider import ConceptRef, LLMProvider, get_provider


class MentorRepo(Repo, Protocol):
    def concepts(self, topic: str) -> list[ConceptRef]: ...
    def attempt_history(
        self, user_id: str, limit: int, offset: int
    ) -> list[dict[str, object]]: ...


class SessionStore(Protocol):
    def ensure_user(self, user_id: str, level: str) -> None: ...
    def create(self, session_id: str, state: AgentState) -> None: ...
    def get(self, session_id: str) -> AgentState | None: ...
    def put(self, session_id: str, state: AgentState) -> None: ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, AgentState] = {}

    def ensure_user(self, user_id: str, level: str) -> None:
        return None

    def create(self, session_id: str, state: AgentState) -> None:
        self._sessions[session_id] = state

    def get(self, session_id: str) -> AgentState | None:
        return self._sessions.get(session_id)

    def put(self, session_id: str, state: AgentState) -> None:
        self._sessions[session_id] = state


class Engine:
    def __init__(
        self,
        provider: LLMProvider,
        repo: MentorRepo,
        store: SessionStore,
        window_size: int,
    ) -> None:
        self.provider = provider
        self.repo = repo
        self.store = store
        self.graph = build_graph(Deps(provider, repo, window_size))

    def start(
        self, user_id: str, topic: str, level: ExplainLevel
    ) -> tuple[str, AgentState]:
        """Create a session and run the first present-turn (review → teach → quiz)."""
        self.store.ensure_user(user_id, level)
        session_id = uuid.uuid4().hex
        initial = AgentState(
            user_id=user_id,
            topic=topic,
            explain_level=level,
            window=[],
            running_summary="",
            answer=None,
            reteach=False,
        )
        self.store.create(session_id, initial)
        final = cast(AgentState, dict(self.graph.invoke(initial)))
        self.store.put(session_id, final)
        return session_id, final

    def turn(
        self, session_id: str, answer: str | None, level: ExplainLevel | None = None
    ) -> AgentState:
        """Advance a session one step (grade/adapt then present the next concept).

        Passing ``level`` with no answer re-teaches the current concept at that
        depth (the on-demand level switch).
        """
        state = self.store.get(session_id)
        if state is None:
            raise KeyError(session_id)
        if level is not None:
            state["explain_level"] = level
        state["answer"] = answer
        final = cast(AgentState, dict(self.graph.invoke(state)))
        self.store.put(session_id, final)
        return final


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Process-wide engine singleton, backend chosen from settings."""
    settings = get_settings()
    provider = get_provider()
    w = settings.context_window_turns
    if settings.database_url.startswith("memory"):
        return Engine(provider, InMemoryRepo(), InMemorySessionStore(), w)

    from app.db.engine import get_engine as get_db_engine
    from app.db.sql_repo import SqlRepo, SqlSessionStore

    db = get_db_engine()
    return Engine(provider, SqlRepo(db), SqlSessionStore(db), w)
