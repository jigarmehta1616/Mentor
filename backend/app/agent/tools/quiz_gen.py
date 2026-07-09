"""quiz_gen tool: generate a targeted question for a concept via the provider."""

from __future__ import annotations

from app.config import ExplainLevel
from app.llm.provider import ConceptRef, LLMProvider


def generate_question(
    provider: LLMProvider, concept: ConceptRef, level: ExplainLevel
) -> str:
    """Produce one targeted quiz question. Delegates to the active provider."""
    return provider.quiz(concept, level)
