"""Tests for the bounded context window + running summary."""

from __future__ import annotations

from app.memory.context import (
    Turn,
    bound,
    default_summarizer,
    render,
    roll,
)

W = 4


def _turn(i: int) -> Turn:
    return Turn(role="user" if i % 2 == 0 else "assistant", content=f"turn-{i}")


def test_window_never_exceeds_size_over_a_long_session() -> None:
    ctx = bound([], W)
    max_seen = 0
    for i in range(1000):
        ctx = roll(ctx.summary, ctx.window, _turn(i), W)
        max_seen = max(max_seen, len(ctx.window))
    # Constant in session length: window is bounded regardless of 1000 turns.
    assert max_seen == W
    assert len(ctx.window) == W


def test_last_w_turns_are_kept_verbatim() -> None:
    ctx = bound([], W)
    for i in range(10):
        ctx = roll(ctx.summary, ctx.window, _turn(i), W)
    assert [t.content for t in ctx.window] == ["turn-6", "turn-7", "turn-8", "turn-9"]


def test_overflow_is_folded_into_summary() -> None:
    ctx = bound([], W)
    for i in range(6):
        ctx = roll(ctx.summary, ctx.window, _turn(i), W)
    # turns 0 and 1 aged out and must be reflected in the summary.
    assert "turn-0" in ctx.summary
    assert "turn-1" in ctx.summary
    # turns still in the window are not (yet) in the summary.
    assert "turn-5" not in ctx.summary


def test_bound_matches_incremental_roll() -> None:
    history = [_turn(i) for i in range(20)]
    batch = bound(history, W)
    incremental = bound([], W)
    for turn in history:
        incremental = roll(incremental.summary, incremental.window, turn, W)
    assert [t.content for t in batch.window] == [t.content for t in incremental.window]


def test_no_summary_when_under_window() -> None:
    ctx = bound([_turn(0), _turn(1)], W)
    assert ctx.summary == ""
    assert len(ctx.window) == 2


def test_render_is_bounded_and_includes_summary() -> None:
    ctx = bound([_turn(i) for i in range(50)], W)
    messages = render("You are Mentor.", ctx.summary, ctx.window)
    # 1 system prompt + 1 summary note + W window turns.
    assert len(messages) == 2 + W
    assert messages[0]["role"] == "system"
    assert "Summary of earlier conversation" in messages[1]["content"]


def test_render_omits_summary_when_empty() -> None:
    ctx = bound([_turn(0)], W)
    messages = render("sys", ctx.summary, ctx.window)
    assert len(messages) == 1 + 1  # system prompt + single turn, no summary note


def test_default_summarizer_truncates_long_turns() -> None:
    long_turn = Turn(role="user", content="x" * 500)
    summary = default_summarizer("", [long_turn])
    assert summary.endswith("...")
    assert len(summary) < 200
