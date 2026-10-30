"""Tests for the clock predicates behind the round timer."""

from herd_mentality.rounds import (
    ROUND_SECONDS,
    round_deadline,
    round_is_over,
    round_is_running,
    seconds_left,
)


def test_deadline_is_thirty_seconds_out():
    assert round_deadline(now=1000.0) == 1000.0 + ROUND_SECONDS


def test_seconds_left_counts_down_and_clamps_at_zero():
    # Also covers a round that was never started, which has no time left.
    assert seconds_left(1030.0, now=1000.0) == 30
    assert seconds_left(1030.0, now=1010.0) == 20
    assert seconds_left(1030.0, now=1040.0) == 0
    assert seconds_left(None, now=1000.0) == 0


def test_round_is_over_exactly_at_the_deadline():
    assert round_is_over(1000.0, now=1000.0) is True
    assert round_is_running(1000.0, now=999.9) is True


def test_a_round_that_never_started_is_neither_running_nor_over():
    # The wrangler can still press Start, so this is not "over".
    assert round_is_running(None, now=1000.0) is False
    assert round_is_over(None, now=1000.0) is False
