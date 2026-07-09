"""The evaluation harness must show adaptive teaching >= static (deterministic)."""

from __future__ import annotations

import pytest

from app.eval.harness import evaluate


@pytest.mark.parametrize("topic", ["neural-networks", "sql"])
def test_adaptive_beats_static(topic: str) -> None:
    results = evaluate(topic)
    static, adaptive = results["static"], results["adaptive"]
    assert adaptive.mastery_rate > static.mastery_rate
    assert adaptive.mean_quality > static.mean_quality
    assert adaptive.mastery_rate == 1.0  # simulated learner masters everything adaptively
