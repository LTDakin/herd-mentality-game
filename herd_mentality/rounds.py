"""The per-round answer clock.

Round state is a deadline timestamp rather than a boolean, so no background
task has to fire at zero: every request compares the deadline to the current
time. Callers may pass `now` so tests never have to sleep.

The deadline alone cannot say whether a round is *waiting to be started*
(nothing has happened yet) or *over* (a clock ran and finished), so those are
two separate predicates and the callers pick the one they mean.
"""

import time

ROUND_SECONDS = 30


def round_deadline(now: float | None = None) -> float:
    """The timestamp a round starting now should end at."""
    if now is None:
        now = time.time()
    return now + ROUND_SECONDS


def seconds_left(round_ends_at: float | None, now: float | None = None) -> int:
    """Whole seconds remaining in the round, clamped at zero.

    Returns 0 when no round is running.
    """
    if round_ends_at is None:
        return 0
    if now is None:
        now = time.time()
    # Round up so a freshly started round reads 30, not 29.
    remaining = round_ends_at - now
    return max(0, int(remaining + 0.999))


def round_is_running(round_ends_at: float | None, now: float | None = None) -> bool:
    """True while the clock is ticking down."""
    if round_ends_at is None:
        return False
    if now is None:
        now = time.time()
    return now < round_ends_at


def round_is_over(round_ends_at: float | None, now: float | None = None) -> bool:
    """True once a clock has been started and then run out.

    A round that was never started is not over: the wrangler can still press
    Start. Use `round_is_running` to tell the two apart.
    """
    if round_ends_at is None:
        return False
    return not round_is_running(round_ends_at, now)
