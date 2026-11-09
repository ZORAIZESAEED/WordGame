import threading
from datetime import date, timedelta

import pytest
from fastapi import Response

from app import daily
from app.db import SessionLocal
from app.main import NewGame, start_daily
from app.models import Game
from app.words import ANSWERS

DAY = date(2026, 11, 20)


@pytest.fixture()
def on_day(monkeypatch):
    """Pin "today" so tests don't depend on the clock. Call it again to move to another day."""

    def _set(day: date) -> None:
        monkeypatch.setattr(daily, "today", lambda: day)

    _set(DAY)
    return _set


# --- choosing the word -------------------------------------------------------


def test_same_word_all_day_and_it_is_an_answer():
    assert daily.word_for(DAY) == daily.word_for(DAY)
    assert daily.word_for(DAY) in ANSWERS


def test_no_repeats_until_every_answer_has_been_used():
    days = [daily.FIRST_DAY + timedelta(days=i) for i in range(len(ANSWERS))]
    assert sorted(daily.word_for(d) for d in days) == sorted(ANSWERS)
    # ...and then the cycle starts again.
    assert daily.word_for(days[0] + timedelta(days=len(ANSWERS))) == daily.word_for(days[0])


def test_the_secret_changes_the_schedule():
    days = [DAY + timedelta(days=i) for i in range(30)]
    a = [daily.word_for(d, secret="one") for d in days]
    b = [daily.word_for(d, secret="two") for d in days]
    assert a != b


def test_secret_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("DAILY_WORD_SECRET", "from-env")
    assert daily.word_for(DAY) == daily.word_for(DAY, secret="from-env")


def test_puzzle_numbers_start_at_one():
    assert daily.puzzle_number(daily.FIRST_DAY) == 1
    assert daily.puzzle_number(daily.FIRST_DAY + timedelta(days=9)) == 10


# --- the API -----------------------------------------------------------------


def test_daily_info_has_no_word(client, on_day):
    body = client.get("/api/daily").json()
    assert body == {"date": "2026-11-20", "number": daily.puzzle_number(DAY)}


def test_everyone_gets_the_same_word(client, on_day):
    a = client.post("/api/daily", json={"player": "ann"}).json()
    b = client.post("/api/daily", json={"player": "bob"}).json()
    assert a["id"] != b["id"]
    assert a["mode"] == b["mode"] == "daily"
    assert a["daily_number"] == daily.puzzle_number(DAY)
    assert a["answer"] is None
    with SessionLocal() as db:
        secrets = {db.get(Game, g["id"]).secret for g in (a, b)}
    assert secrets == {daily.word_for(DAY)}


def test_starting_again_resumes_the_same_game(client, on_day):
    first = client.post("/api/daily", json={"player": "ann"})
    assert first.status_code == 201
    gid = first.json()["id"]
    client.post(f"/api/games/{gid}/guesses", json={"word": "about"})

    again = client.post("/api/daily", json={"player": " ann "})  # trimmed, so same player
    assert again.status_code == 200
    assert again.json()["id"] == gid
    assert again.json()["attempts_used"] == 1


def test_one_daily_game_per_day_even_after_finishing(client, on_day):
    gid = client.post("/api/daily", json={"player": "ann"}).json()["id"]
    r = client.post(f"/api/games/{gid}/guesses", json={"word": daily.word_for(DAY)})
    assert r.json()["status"] == "won"

    again = client.post("/api/daily", json={"player": "ann"}).json()
    assert again["id"] == gid
    assert again["status"] == "won"
    assert again["answer"] == daily.word_for(DAY)  # finished, so the answer shows


def test_a_new_day_brings_a_new_game(client, on_day):
    first = client.post("/api/daily", json={"player": "ann"}).json()
    on_day(DAY + timedelta(days=1))
    second = client.post("/api/daily", json={"player": "ann"}).json()
    assert second["id"] != first["id"]
    assert second["daily_number"] == first["daily_number"] + 1


def test_practice_is_still_unlimited(client, on_day):
    client.post("/api/daily", json={"player": "ann"})
    ids = {client.post("/api/games", json={"player": "ann"}).json()["id"] for _ in range(3)}
    assert len(ids) == 3
    game = client.get(f"/api/games/{ids.pop()}").json()
    assert game["mode"] == "practice"
    assert game["daily_number"] is None


def test_daily_leaderboard_only_shows_todays_winners(client, on_day):
    word = daily.word_for(DAY)

    def play(player: str, guesses: list[str]) -> None:
        gid = client.post("/api/daily", json={"player": player}).json()["id"]
        for w in guesses:
            client.post(f"/api/games/{gid}/guesses", json={"word": w})

    play("slow", ["about", word])
    play("fast", [word])
    play("loser", ["about"] * 6)
    client.post("/api/games", json={"player": "practice-only"})

    board = client.get("/api/daily/leaderboard").json()
    assert [r["player"] for r in board] == ["fast", "slow"]

    on_day(DAY + timedelta(days=1))
    assert client.get("/api/daily/leaderboard").json() == []


def test_simultaneous_starts_make_one_game(client, on_day):
    # Double-clicking "Daily" sends two requests at once; the unique constraint keeps it
    # to one game either way.
    threads_n = 6
    barrier = threading.Barrier(threads_n)
    ids: list[str | None] = [None] * threads_n

    def worker(i: int) -> None:
        db = SessionLocal()
        try:
            barrier.wait()
            ids[i] = start_daily(NewGame(player="clicker"), Response(), db).id
        finally:
            db.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(threads_n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert None not in ids
    assert len(set(ids)) == 1
    with SessionLocal() as db:
        assert db.query(Game).filter(Game.player == "clicker").count() == 1
