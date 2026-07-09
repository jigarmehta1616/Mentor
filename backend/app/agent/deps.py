"""Dependencies injected into the agent nodes."""

from __future__ import annotations

from dataclasses import dataclass

from app.agent.repo import Repo
from app.llm.provider import LLMProvider


@dataclass
class Deps:
    provider: LLMProvider
    repo: Repo
    window_size: int
