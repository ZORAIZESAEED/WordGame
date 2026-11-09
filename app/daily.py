"""The daily challenge: one word per UTC day, the same for every player.

The answers are shuffled once with a fixed seed, and day N of the challenge uses the
Nth word of that shuffle. So every server works out the same word without storing
anything, and no word comes round again until the whole list has been used.

The seed comes from DAILY_WORD_SECRET. Locally the default is fine. A public deployment
should set its own value, or anyone reading this repo could work out upcoming words.
"""

import os
import random
from datetime import UTC, date, datetime
from functools import cache

from .words import ANSWERS

# Day 1 of the challenge. Changing it renumbers every puzzle, so leave it alone.
FIRST_DAY = date(2026, 11, 1)

DEFAULT_SECRET = "wordgame-dev"


def today() -> date:
    """The current challenge day. Days roll over at midnight UTC."""
    return datetime.now(UTC).date()


def puzzle_number(day: date) -> int:
    return (day - FIRST_DAY).days + 1


@cache
def _order(secret: str, answers: tuple[str, ...]) -> list[str]:
    # Sort first so the order doesn't depend on how the file happens to be arranged.
    return random.Random(secret).sample(sorted(answers), len(answers))


def word_for(day: date, secret: str | None = None) -> str:
    if secret is None:
        secret = os.getenv("DAILY_WORD_SECRET", DEFAULT_SECRET)
    order = _order(secret, tuple(ANSWERS))
    return order[(day - FIRST_DAY).days % len(order)]
