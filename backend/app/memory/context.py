"""Bounded agent context: a sliding window of the last W turns plus a running
summary of everything older.

The LLM never receives unbounded history. Loading the context for a call costs
O(W) tokens and is constant in session length: we keep at most W verbatim turns
and fold each overflow turn into a single running summary as it ages out.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

# (previous_summary, turns_being_folded) -> new_summary
Summarizer = Callable[[str, "list[Turn]"], str]


@dataclass(frozen=True)
class Turn:
    role: str
    content: str


@dataclass(frozen=True)
class BoundedContext:
    summary: str
    window: list[Turn]


def approx_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token). O(1) in length via len()."""
    return (len(text) + 3) // 4


def default_summarizer(prev_summary: str, folded: list[Turn]) -> str:
    """Cheap extractive summary so the app works with no LLM. O(len(folded)).

    Only ever called on the overflow turns (usually one), so amortized O(1).
    """
    lines = [prev_summary] if prev_summary else []
    for turn in folded:
        snippet = turn.content.strip().replace("\n", " ")
        if len(snippet) > 160:
            snippet = snippet[:157] + "..."
        lines.append(f"- {turn.role}: {snippet}")
    return "\n".join(lines).strip()


def roll(
    summary: str,
    window: Sequence[Turn],
    new_turn: Turn,
    window_size: int,
    summarizer: Summarizer = default_summarizer,
) -> BoundedContext:
    """Append one turn; fold any overflow (oldest) turns into the summary.

    Amortized O(1): each turn is folded at most once over its lifetime.
    """
    combined = [*window, new_turn]
    if len(combined) <= window_size:
        return BoundedContext(summary, combined)
    overflow = combined[:-window_size]
    kept = combined[-window_size:]
    return BoundedContext(summarizer(summary, overflow), kept)


def bound(
    history: Sequence[Turn],
    window_size: int,
    summarizer: Summarizer = default_summarizer,
) -> BoundedContext:
    """Collapse a full history into (summary, last-W-turns). Output is O(W).

    Convenience/rebuild path; the hot path uses :func:`roll` incrementally.
    """
    if len(history) <= window_size:
        return BoundedContext("", list(history))
    overflow = list(history[:-window_size])
    kept = list(history[-window_size:])
    return BoundedContext(summarizer("", overflow), kept)


def render(
    system_prompt: str, summary: str, window: Sequence[Turn]
) -> list[dict[str, str]]:
    """Build the bounded message list sent to the LLM. O(W) messages/tokens.

    The summary is injected as a system note so older context survives without
    resending it turn by turn.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if summary:
        messages.append(
            {"role": "system", "content": f"Summary of earlier conversation:\n{summary}"}
        )
    messages.extend({"role": t.role, "content": t.content} for t in window)
    return messages
