from datetime import date, timedelta

import pytest

from app import daily
from app.stats import DailyResult, daily_stats

TODAY = date(2026, 11, 20)


def day(n: int) -> date:
    """n days before TODAY (0 is today)."""
    return TODAY - timedelta(days=n)


def won(n: int, attempts: int = 3) -> DailyResult:
    return DailyResult(day=day(n), won=True, attempts=attempts)


def lost(n: int) -> DailyResult:
    return DailyResult(day=day(n), won=False, attempts=6)


# --- the calculation ---------------------------------------------------------


def test_no_games():
    s = daily_stats([], TODAY)
    assert (s.played, s.wins, s.win_rate, s.current_streak, s.max_streak) == (0, 0, 0, 0, 0)
    assert s.distribution == [0] * 6


def test_win_rate_and_distribution():
    s = daily_stats([won(0, 1), won(1, 3), won(2, 3), lost(3)], TODAY)
    assert (s.played, s.wins, s.win_rate) == (4, 3, 75)
    assert s.distribution == [1, 0, 2, 0, 0, 0]


def test_streak_counts_today():
    assert daily_stats([won(0), won(1), won(2)], TODAY).current_streak == 3


def test_streak_survives_until_today_is_played():
    # Won yesterday and the day before, haven't finished today yet.
    assert daily_stats([won(1), won(2)], TODAY).current_streak == 2


def test_losing_today_ends_the_streak():
    s = daily_stats([lost(0), won(1), won(2)], TODAY)
    assert s.current_streak == 0
    assert s.max_streak == 2


def test_a_missed_day_ends_the_streak():
    s = daily_stats([won(0), won(2), won(3), won(4)], TODAY)
    assert s.current_streak == 1
    assert s.max_streak == 3


def test_old_streaks_count_towards_the_best():
    results = [won(n) for n in range(10, 15)] + [won(0)]
    s = daily_stats(results, TODAY)
    assert (s.current_streak, s.max_streak) == (1, 5)


# --- the endpoint ------------------------------------------------------------


@pytest.fixture()
def play_daily(client, monkeypatch):
    """Play one daily game as `player` on a given day, with the given guesses."""

    def _play(player: str, on: date, guesses: list[str]) -> dict:
        monkeypatch.setattr(daily, "today", lambda: on)
        gid = client.post("/api/daily", json={"player": player}).json()["id"]
        body = None
        for w in guesses:
            body = client.post(f"/api/games/{gid}/guesses", json={"word": w}).json()
        return body

    return _play


def test_stats_endpoint(client, play_daily, force_secret, monkeypatch):
    play_daily("ann", day(2), [daily.word_for(day(2))])  # won in 1
    play_daily("ann", day(1), ["about", daily.word_for(day(1))])  # won in 2
    play_daily("ann", day(0), ["about"])  # today, still playing: not counted
    play_daily("bob", day(1), [daily.word_for(day(1))])  # someone else

    gid = client.post("/api/games", json={"player": "ann"}).json()["id"]
    force_secret(gid, "crane")
    client.post(f"/api/games/{gid}/guesses", json={"word": "crane"})
    client.post("/api/games", json={"player": "ann"})  # unfinished practice

    monkeypatch.setattr(daily, "today", lambda: TODAY)
    body = client.get("/api/players/ann/stats").json()
    assert body["player"] == "ann"
    assert body["daily"] == {
        "played": 2,
        "wins": 2,
        "win_rate": 100,
        "current_streak": 2,  # today isn't finished, so the streak runs from yesterday
        "max_streak": 2,
        "distribution": [1, 1, 0, 0, 0, 0],
    }
    assert body["practice"] == {"played": 1, "wins": 1}


def test_stats_for_a_new_player_are_zero(client):
    body = client.get("/api/players/nobody/stats").json()
    assert body["daily"]["played"] == 0
    assert body["practice"] == {"played": 0, "wins": 0}


def test_stats_reject_overlong_names(client):
    assert client.get("/api/players/" + "x" * 33 + "/stats").status_code == 422
