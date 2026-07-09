"""OpenAI-backed provider. Optional dependency; only imported when
LLM_PROVIDER=openai.
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

_MODEL = "gpt-4o-mini"

_LEVEL_INSTRUCTION: dict[str, str] = {
    "eli5": "Explain like the learner is five, using a simple analogy.",
    "student": "Explain at the level of an engaged undergraduate.",
    "expert": "Explain at an expert level, precise and dense.",
}


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str) -> None:
        from openai import OpenAI

        self._client: Any = OpenAI(api_key=api_key or None)

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
            f"Teach '{concept.name}'. Context: {concept.summary}\n"
            f"~150 words. Cite these inline as [n] if used:\n{cited}"
        )
        stream = self._client.chat.completions.create(
            model=_MODEL,
            stream=True,
            messages=[
                {"role": "system", "content": self._system(level)},
                {"role": "user", "content": prompt},
            ],
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def quiz(self, concept: ConceptRef, level: ExplainLevel) -> str:
        resp = self._client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": self._system(level)},
                {
                    "role": "user",
                    "content": f"Write ONE short quiz question testing '{concept.name}'. "
                    f"Context: {concept.summary}. Return only the question.",
                },
            ],
        )
        return resp.choices[0].message.content or ""

    def grade(self, concept: ConceptRef, question: str, answer: str) -> GradeResult:
        data = self._json_call(
            "Grade the learner's answer for spaced repetition. "
            'Return JSON {"quality": 0-5 int, "misconception": string, "feedback": string}.',
            f"Concept: {concept.name} — {concept.summary}\nQ: {question}\nA: {answer}",
        )
        return GradeResult(
            max(0, min(5, int(data.get("quality", 2)))),
            str(data.get("misconception", "")),
            str(data.get("feedback", "")),
        )

    def diagnose(
        self, concept: ConceptRef, question: str, answer: str, grade: GradeResult
    ) -> Diagnosis:
        data = self._json_call(
            'Return JSON {"misconception": string, "subpoint": string, "remediation": string} '
            "identifying the single sub-point to re-teach.",
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
        resp = self._client.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": f"Existing summary:\n{prev_summary}\n\nNew turns:\n{convo}\n\n"
                    "Return an updated compact summary (<=120 words).",
                }
            ],
        )
        return resp.choices[0].message.content or prev_summary

    def _json_call(self, system: str, user: str) -> dict[str, Any]:
        resp = self._client.chat.completions.create(
            model=_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        try:
            return dict(json.loads(resp.choices[0].message.content or "{}"))
        except (json.JSONDecodeError, TypeError):
            return {}
