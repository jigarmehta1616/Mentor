"""LLM provider abstraction: mock | anthropic | openai.

The provider exposes the small set of *pedagogical* operations the agent needs
(teach, quiz, grade, diagnose, summarize). The mock implements them with
deterministic heuristics so the whole app runs with **no API keys and no cost**;
the real providers implement them by prompting a model.

Design rule: the model only *explains and diagnoses*. All scheduling math is
deterministic code in ``memory/srs.py`` — never the LLM.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

from app.config import ExplainLevel, get_settings

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "are", "for",
    "with", "that", "this", "it", "as", "by", "from", "how", "what", "why",
    "into", "than", "then", "over", "you", "your", "its", "be", "we", "they",
}


@dataclass(frozen=True)
class Citation:
    title: str
    url: str


@dataclass(frozen=True)
class GradeResult:
    """Structured grader output. ``quality`` (0..5) feeds SM-2 directly."""

    quality: int
    misconception: str
    feedback: str


@dataclass(frozen=True)
class Diagnosis:
    """What the learner got wrong and the specific sub-point to re-teach."""

    misconception: str
    subpoint: str
    remediation: str


@dataclass(frozen=True)
class Resource:
    title: str
    url: str
    snippet: str = ""


@dataclass(frozen=True)
class ConceptRef:
    """Minimal concept info the provider needs, decoupled from the DB layer."""

    id: str
    name: str
    summary: str = ""
    keywords: list[str] = field(default_factory=list)


def keywords_of(text: str, limit: int = 8) -> list[str]:
    """Extract salient lowercase keywords from text. O(len(text))."""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    seen: dict[str, None] = {}
    for w in words:
        if w not in _STOPWORDS:
            seen.setdefault(w, None)
    return list(seen)[:limit]


def _covered(keyword: str, answer_words: set[str]) -> bool:
    """True if the answer addresses ``keyword`` (tolerant of stem variants). O(k)."""
    stem = keyword[:5]
    return any(
        w == keyword or w.startswith(stem) or keyword.startswith(w[:5]) for w in answer_words
    )


class LLMProvider(Protocol):
    name: str

    def teach(
        self, concept: ConceptRef, level: ExplainLevel, resources: list[Resource]
    ) -> str: ...

    def stream_teach(
        self, concept: ConceptRef, level: ExplainLevel, resources: list[Resource]
    ) -> Iterator[str]: ...

    def quiz(self, concept: ConceptRef, level: ExplainLevel) -> str: ...

    def grade(self, concept: ConceptRef, question: str, answer: str) -> GradeResult: ...

    def diagnose(
        self, concept: ConceptRef, question: str, answer: str, grade: GradeResult
    ) -> Diagnosis: ...

    def summarize(self, prev_summary: str, folded: list[tuple[str, str]]) -> str: ...


# --- Mock provider -----------------------------------------------------------
_LEVEL_TONE: dict[str, str] = {
    "eli5": "Imagine you're five: ",
    "student": "Here's the student-level view: ",
    "expert": "At an expert level: ",
}


class MockProvider:
    """Deterministic, offline provider. Real enough to demo the full loop."""

    name = "mock"

    def teach(
        self, concept: ConceptRef, level: ExplainLevel, resources: list[Resource]
    ) -> str:
        return "".join(self.stream_teach(concept, level, resources))

    def stream_teach(
        self, concept: ConceptRef, level: ExplainLevel, resources: list[Resource]
    ) -> Iterator[str]:
        tone = _LEVEL_TONE.get(level, _LEVEL_TONE["student"])
        yield f"**{concept.name}**\n\n{tone}"
        yield concept.summary or f"{concept.name} is a key idea in this topic."
        kws = concept.keywords or keywords_of(concept.summary)
        if kws:
            yield f"\n\nThe core ideas to hold onto are: {', '.join(kws[:4])}."
        if resources:
            cites = " ".join(f"[{i + 1}]({r.url})" for i, r in enumerate(resources[:3]))
            yield f"\n\nSources: {cites}"

    def quiz(self, concept: ConceptRef, level: ExplainLevel) -> str:
        kws = concept.keywords or keywords_of(concept.summary)
        focus = kws[0] if kws else concept.name
        return (
            f"In your own words, explain **{concept.name}** — "
            f"and be sure to address the role of *{focus}*."
        )

    def grade(self, concept: ConceptRef, question: str, answer: str) -> GradeResult:
        """Heuristic grade from keyword overlap. Deterministic, O(len(answer))."""
        expected = concept.keywords or keywords_of(f"{concept.name} {concept.summary}")
        answer_words = set(keywords_of(answer, limit=64))
        if not answer.strip():
            return GradeResult(0, "no answer given", "You left the answer blank.")
        if not expected:
            quality = 4 if len(answer_words) >= 3 else 2
            return GradeResult(quality, "", "Reasonable attempt.")
        hits = [w for w in expected if _covered(w, answer_words)]
        missed = [w for w in expected if not _covered(w, answer_words)]
        ratio = len(hits) / len(expected)
        quality = max(0, min(5, round(ratio * 5)))
        misconception = "" if quality >= 3 else f"missing the role of {missed[0]}" if missed else ""
        feedback = (
            "Solid — you covered the key ideas."
            if quality >= 3
            else f"You didn't touch on {', '.join(missed[:2])}."
        )
        return GradeResult(quality, misconception, feedback)

    def diagnose(
        self, concept: ConceptRef, question: str, answer: str, grade: GradeResult
    ) -> Diagnosis:
        expected = concept.keywords or keywords_of(f"{concept.name} {concept.summary}")
        answer_words = set(keywords_of(answer, limit=64))
        missed = [w for w in expected if not _covered(w, answer_words)]
        subpoint = missed[0] if missed else (grade.misconception or concept.name)
        return Diagnosis(
            misconception=grade.misconception or f"unclear on {subpoint}",
            subpoint=subpoint,
            remediation=f"Re-explain how **{subpoint}** fits into {concept.name}.",
        )

    def summarize(self, prev_summary: str, folded: list[tuple[str, str]]) -> str:
        parts = [prev_summary] if prev_summary else []
        for role, content in folded:
            snippet = content.strip().replace("\n", " ")[:140]
            parts.append(f"- {role}: {snippet}")
        return "\n".join(parts).strip()


@lru_cache(maxsize=1)
def get_provider() -> LLMProvider:
    """Return the configured provider (process singleton). O(1) after first call."""
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings.anthropic_api_key)
    if settings.llm_provider == "openai":
        from app.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(settings.openai_api_key)
    return MockProvider()
