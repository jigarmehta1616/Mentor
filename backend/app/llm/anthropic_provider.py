"""Anthropic-backed provider. Optional dependency; only imported when
LLM_PROVIDER=anthropic. Uses adaptive thinking; structured fields (grade,
diagnosis) are requested as JSON and parsed, which stays robust across SDK
versions. The client is dynamically typed (Any) because the exact SDK surface
depends on the installed anthropic version.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from app.config import ExplainLevel
from app.llm.provider import (
    ConceptRef,
    Diagnosis,
    GradeResult,
    Resource,
    keywords_of,
)

_MODEL = "claude-opus-4-8"

_LEVEL_INSTRUCTION: dict[str, str] = {
    "eli5": "Explain like the learner is five years old, using a simple analogy.",
    "student": "Explain at the level of an engaged undergraduate student.",
    "expert": "Explain at an expert level, precise and dense.",
}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str) -> None:
        import anthropic

        self._client: Any = anthropic.Anthropic(api_key=api_key or None)

    def _system(self, level: ExplainLevel) -> str:
        return "You are Mentor, an expert tutor. " + _LEVEL_INSTRUCTION.get(
            level, _LEVEL_INSTRUCTION["student"]
        )

    def teach(
        self, concept: ConceptRef, level: ExplainLevel, resources: list[Resource]
    ) -> str:
        return "".join(self.stream_teach(concept, level, resources))

    def stream_teach(
        self, concept: ConceptRef, level: ExplainLevel, resources: list[Resource]
    ) -> Iterator[str]:
        cited = "\n".join(f"- {r.title}: {r.url}" for r in resources[:3])
        prompt = (
            f"Teach the concept '{concept.name}'. Context: {concept.summary}\n"
            f"~150 words. If you use these sources, cite them inline as [n]:\n{cited}"
        )
        with self._client.messages.stream(
            model=_MODEL,
            max_tokens=1024,
            system=self._system(level),
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            yield from stream.text_stream

    def quiz(self, concept: ConceptRef, level: ExplainLevel) -> str:
        resp = self._client.messages.create(
            model=_MODEL,
            max_tokens=256,
            system=self._system(level),
            messages=[
                {
                    "role": "user",
                    "content": f"Write ONE short quiz question testing '{concept.name}'. "
                    f"Context: {concept.summary}. Return only the question.",
                }
            ],
        )
        return _first_text(resp)

    def grade(self, concept: ConceptRef, question: str, answer: str) -> GradeResult:
        data = self._json_call(
            'Return ONLY JSON: {"quality": 0-5 integer (SM-2 recall quality), '
            '"misconception": string (empty if correct), "feedback": string}.',
            f"Concept: {concept.name} — {concept.summary}\nQ: {question}\nA: {answer}",
        )
        return GradeResult(
            int(max(0, min(5, int(data.get("quality", 2))))),
            str(data.get("misconception", "")),
            str(data.get("feedback", "")),
        )

    def diagnose(
        self, concept: ConceptRef, question: str, answer: str, grade: GradeResult
    ) -> Diagnosis:
        data = self._json_call(
            'Return ONLY JSON: {"misconception": string, "subpoint": string, '
            '"remediation": string} identifying the single sub-point to re-teach.',
            f"Concept: {concept.name} — {concept.summary}\nQ: {question}\nA: {answer}\n"
            f"Detected: {grade.misconception}",
        )
        sub = str(data.get("subpoint") or (keywords_of(concept.summary)[:1] or [concept.name])[0])
        return Diagnosis(
            str(data.get("misconception", grade.misconception)),
            sub,
            str(data.get("remediation", f"Re-explain {sub}.")),
        )

    def summarize(self, prev_summary: str, folded: list[tuple[str, str]]) -> str:
        convo = "\n".join(f"{role}: {content}" for role, content in folded)
        resp = self._client.messages.create(
            model=_MODEL,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": f"Existing summary:\n{prev_summary}\n\nNew turns:\n{convo}\n\n"
                    "Return an updated compact summary (<=120 words).",
                }
            ],
        )
        return _first_text(resp) or prev_summary

    def _json_call(self, system: str, user: str) -> dict[str, Any]:
        resp = self._client.messages.create(
            model=_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        try:
            return dict(json.loads(_first_text(resp) or "{}"))
        except (json.JSONDecodeError, TypeError):
            return {}


def _first_text(resp: Any) -> str:
    """Extract the first text block from a Messages response."""
    for block in getattr(resp, "content", []):
        if getattr(block, "type", None) == "text":
            return str(block.text)
    return ""
