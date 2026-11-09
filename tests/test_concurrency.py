"""Guesses sent at the same moment must not get past the six-attempt limit.

The endpoint reads the game, checks how many guesses it has, then writes a new one.
Without a lock, several requests can all read "5 guesses so far" before any of them
commits, and every one of them gets saved. These tests fire requests from real threads,
each with its own database session, the way concurrent HTTP requests would arrive.
"""

import threading

import pytest
from fastapi import HTTPException

from app import game as logic
from app.db import SessionLocal
from app.main import GuessIn, make_guess
from app.models import Game, Guess

THREADS = 8


def _guess_at_once(game_id: str, word: str) -> list[object]:
    """Send THREADS guesses for one game at the same instant. Returns each outcome."""
    barrier = threading.Barrier(THREADS)
    results: list[object] = [None] * THREADS

    def worker(i: int) -> None:
        db = SessionLocal()
        try:
            barrier.wait()
            make_guess(game_id, GuessIn(word=word), db)
            results[i] = "ok"
        except HTTPException as e:
            results[i] = e.status_code
        except Exception as e:  # anything else is a bug; report it rather than hang
            results[i] = repr(e)
        finally:
            db.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return results


def _stored_guesses(game_id: str) -> int:
    with SessionLocal() as db:
        return db.query(Guess).filter(Guess.game_id == game_id).count()


@pytest.mark.parametrize("round_", range(5))  # races are timing-dependent, so try a few times
def test_last_attempt_can_only_be_used_once(client, force_secret, round_):
    gid = client.post("/api/games", json={"player": "racer"}).json()["id"]
    force_secret(gid, "crane")
    for _ in range(logic.MAX_ATTEMPTS - 1):
        client.post(f"/api/games/{gid}/guesses", json={"word": "about"})

    results = _guess_at_once(gid, "about")

    assert results.count("ok") == 1, results
    assert results.count(409) == THREADS - 1, results
    assert _stored_guesses(gid) == logic.MAX_ATTEMPTS
    with SessionLocal() as db:
        assert db.get(Game, gid).status == "lost"


@pytest.mark.parametrize("round_", range(5))
def test_simultaneous_guesses_on_a_fresh_game_stop_at_six(client, force_secret, round_):
    gid = client.post("/api/games", json={"player": "racer"}).json()["id"]
    force_secret(gid, "crane")

    results = _guess_at_once(gid, "about")  # 8 requests, only 6 attempts

    assert results.count("ok") == logic.MAX_ATTEMPTS, results
    assert results.count(409) == THREADS - logic.MAX_ATTEMPTS, results
    assert _stored_guesses(gid) == logic.MAX_ATTEMPTS
