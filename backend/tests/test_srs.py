"""Tests for the SM-2 spaced-repetition scheduler."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.memory.srs import DEFAULT_EF, MIN_EF, SRSState, update

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_first_successful_review_interval_is_one_day() -> None:
    result = update(SRSState(), quality=4, now=NOW)
    assert result.repetitions == 1
    assert result.interval_days == 1
    assert result.next_review == datetime(2026, 1, 2, tzinfo=UTC)


def test_second_success_interval_is_six_days() -> None:
    s = update(SRSState(), quality=5, now=NOW)  # rep 1 -> interval 1
    s = update(s, quality=5, now=NOW)  # rep 2 -> interval 6
    assert s.repetitions == 2
    assert s.interval_days == 6


def test_third_success_scales_by_easiness_factor() -> None:
    s = SRSState()
    s = update(s, quality=5, now=NOW)  # rep 1, interval 1
    s = update(s, quality=5, now=NOW)  # rep 2, interval 6
    ef_before_third = s.easiness_factor
    s = update(s, quality=5, now=NOW)  # rep 3, interval = round(6 * EF_before)
    assert s.repetitions == 3
    # Interval uses the EF *before* this review's bump, per SM-2.
    assert s.interval_days == round(6 * ef_before_third)
    assert s.interval_days >= 15


def test_failure_resets_streak_and_reviews_tomorrow() -> None:
    s = SRSState()
    for _ in range(3):
        s = update(s, quality=5, now=NOW)
    failed = update(s, quality=1, now=NOW)
    assert failed.repetitions == 0
    assert failed.interval_days == 1
    assert failed.next_review == datetime(2026, 1, 2, tzinfo=UTC)


def test_easiness_factor_floored_at_min() -> None:
    s = SRSState()
    for _ in range(10):
        s = update(s, quality=0, now=NOW)
    assert s.easiness_factor == pytest.approx(MIN_EF)


def test_easiness_factor_grows_on_perfect_recall() -> None:
    result = update(SRSState(), quality=5, now=NOW)
    assert result.easiness_factor > DEFAULT_EF


def test_mastery_rises_with_success_and_falls_with_failure() -> None:
    good = update(SRSState(), quality=5, now=NOW)
    assert good.mastery_level > 0.0
    bad = update(good, quality=0, now=NOW)
    assert bad.mastery_level < good.mastery_level
    assert 0.0 <= bad.mastery_level <= 1.0


@pytest.mark.parametrize("quality", [-1, 6, 10])
def test_out_of_range_quality_rejected(quality: int) -> None:
    with pytest.raises(ValueError):
        update(SRSState(), quality=quality, now=NOW)


def test_last_score_recorded() -> None:
    assert update(SRSState(), quality=3, now=NOW).last_score == 3
