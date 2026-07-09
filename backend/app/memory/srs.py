"""SM-2 spaced repetition.

The scheduling math is deterministic and lives here (the LLM never does it). A
review takes an SM-2 *quality* in 0..5 and produces the next interval, easiness
factor, and due date. Pure functions — trivially testable, no I/O.

Reference: the SuperMemo SM-2 algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

MIN_EF = 1.3
DEFAULT_EF = 2.5
PASS_THRESHOLD = 3  # quality >= 3 counts as a successful recall


@dataclass(frozen=True)
class SRSState:
    """Compact per-(user, concept) SM-2 state. This is all that lives on the hot path."""

    easiness_factor: float = DEFAULT_EF
    interval_days: int = 0
    repetitions: int = 0
    mastery_level: float = 0.0
    last_score: int | None = None
    next_review: datetime | None = None


def _next_ef(ef: float, quality: int) -> float:
    """New easiness factor per SM-2, floored at 1.3. O(1)."""
    updated = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    return max(MIN_EF, updated)


def _next_mastery(current: float, quality: int) -> float:
    """Exponential moving average of normalized quality, clamped to [0, 1]. O(1)."""
    target = quality / 5.0
    updated = 0.6 * current + 0.4 * target
    return max(0.0, min(1.0, updated))


def update(state: SRSState, quality: int, now: datetime) -> SRSState:
    """Apply one SM-2 review and return the new state (with next_review). O(1).

    quality < 3 resets the repetition streak and reviews again tomorrow; quality
    >= 3 grows the interval geometrically by the easiness factor.
    """
    if not 0 <= quality <= 5:
        raise ValueError(f"quality must be in 0..5, got {quality}")

    if quality >= PASS_THRESHOLD:
        if state.repetitions == 0:
            interval = 1
        elif state.repetitions == 1:
            interval = 6
        else:
            interval = round(state.interval_days * state.easiness_factor)
        repetitions = state.repetitions + 1
    else:
        interval = 1
        repetitions = 0

    return replace(
        state,
        easiness_factor=_next_ef(state.easiness_factor, quality),
        interval_days=interval,
        repetitions=repetitions,
        mastery_level=_next_mastery(state.mastery_level, quality),
        last_score=quality,
        next_review=now + timedelta(days=interval),
    )


# --- Due-query helper --------------------------------------------------------
# Pull due items via the B-tree index idx_due (user_id, next_review):
#   WHERE next_review <= now ORDER BY next_review LIMIT k  ->  O(log n + k).
DUE_QUERY = (
    "SELECT concept_id, next_review, easiness_factor, interval_days, "
    "repetitions, mastery_level, last_score "
    "FROM mastery "
    "WHERE user_id = :user_id AND next_review IS NOT NULL AND next_review <= :now "
    "ORDER BY next_review ASC "
    "LIMIT :limit"
)
