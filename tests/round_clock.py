"""Test helper for putting a round's clock at a chosen point in time.

Kept out of conftest.py so tests can import it directly instead of reaching
into the pytest conftest module.
"""

import time

from herd_mentality.state import Game_State

ROUND_SECONDS = 30


def start_clock(seconds_left: int = ROUND_SECONDS) -> None:
    """Set the round's deadline `seconds_left` from now, without sleeping.

    Pass a negative value to simulate a round whose clock has run out.
    """
    Game_State["round_ends_at"] = time.time() + seconds_left
