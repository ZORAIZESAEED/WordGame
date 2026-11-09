"""Player statistics, worked out from finished games. No web or database code in here."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta

from .game import MAX_ATTEMPTS


@dataclass(frozen=True)
class DailyResult:
    day: date
    won: bool
    attempts: int


@dataclass
class DailyStats:
    played: int = 0
    wins: int = 0
    win_rate: int = 0  # whole percent
    current_streak: int = 0
    max_streak: int = 0
    # How many wins took 1 guess, 2 guesses, ... MAX_ATTEMPTS guesses.
    distribution: list[int] = field(default_factory=lambda: [0] * MAX_ATTEMPTS)


def daily_stats(results: Iterable[DailyResult], today: date) -> DailyStats:
    """Stats over finished daily games.

    A streak is a run of consecutive days with a daily win. Today's streak survives until
    today's game is lost: if you haven't finished today yet, it's still counted from yesterday.
    """
    results = list(results)
    stats = DailyStats(played=len(results))
    if not results:
        return stats

    won_days = {r.day for r in results if r.won}
    lost_days = {r.day for r in results if not r.won}
    stats.wins = len(won_days)
    stats.win_rate = round(100 * stats.wins / stats.played)
    for r in results:
        if r.won and 1 <= r.attempts <= MAX_ATTEMPTS:
            stats.distribution[r.attempts - 1] += 1

    if today not in lost_days:
        day = today if today in won_days else today - timedelta(days=1)
        while day in won_days:
            stats.current_streak += 1
            day -= timedelta(days=1)

    run = 0
    previous = None
    for day in sorted(won_days):
        run = run + 1 if previous == day - timedelta(days=1) else 1
        stats.max_streak = max(stats.max_streak, run)
        previous = day

    return stats
