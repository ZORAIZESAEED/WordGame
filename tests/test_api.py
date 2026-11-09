import os

# Use a throwaway database for the whole test run. Must be set before importing the app.
# Defaults to SQLite. Set TEST_DATABASE_URL to run the same tests against Postgres.
# (Deliberately not DATABASE_URL: the tests drop every table, so never point them at real data.)
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_wordgame.db")

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Game


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # lifespan creates tables
        yield c


def _force_secret(game_id: str, word: str):
    with SessionLocal() as db:
        g = db.get(Game, game_id)
        g.secret = word
        db.commit()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_new_game_hides_the_answer(client):
    r = client.post("/api/games", json={"player": "zoraize"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "playing"
    assert body["answer"] is None
    assert body["max_attempts"] == 6


def test_win_flow_and_leaderboard(client):
    gid = client.post("/api/games", json={"player": "zoraize"}).json()["id"]
    _force_secret(gid, "crane")

    r = client.post(f"/api/games/{gid}/guesses", json={"word": "slate"})
    assert r.status_code == 200 and r.json()["status"] == "playing"

    r = client.post(f"/api/games/{gid}/guesses", json={"word": "crane"})
    body = r.json()
    assert body["status"] == "won"
    assert body["score"] == 500  # won on attempt 2
    assert body["answer"] == "crane"

    board = client.get("/api/leaderboard").json()
    assert board == [{"player": "zoraize", "score": 500}]


def test_lose_after_six_wrong_guesses(client):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    _force_secret(gid, "crane")
    for _ in range(6):
        r = client.post(f"/api/games/{gid}/guesses", json={"word": "about"})
    assert r.json()["status"] == "lost"
    assert r.json()["answer"] == "crane"
    assert client.get("/api/leaderboard").json() == []


def test_cannot_guess_after_game_over(client):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    _force_secret(gid, "crane")
    client.post(f"/api/games/{gid}/guesses", json={"word": "crane"})
    r = client.post(f"/api/games/{gid}/guesses", json={"word": "about"})
    assert r.status_code == 409


def test_rejects_words_not_in_list(client):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    r = client.post(f"/api/games/{gid}/guesses", json={"word": "zzzzz"})
    assert r.status_code == 422


def test_player_name_is_trimmed(client):
    r = client.post("/api/games", json={"player": "  zoraize  "})
    assert r.status_code == 201
    assert r.json()["player"] == "zoraize"


@pytest.mark.parametrize("name", ["", "   ", "x" * 33])
def test_rejects_bad_player_names(client, name):
    assert client.post("/api/games", json={"player": name}).status_code == 422


def test_guess_is_case_insensitive(client):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    _force_secret(gid, "crane")
    body = client.post(f"/api/games/{gid}/guesses", json={"word": "CRANE"}).json()
    assert body["status"] == "won"
    assert body["guesses"][0]["word"] == "crane"


def test_leaderboard_orders_by_score(client):
    for player, guesses in [("slow", ["slate", "crane"]), ("fast", ["crane"])]:
        gid = client.post("/api/games", json={"player": player}).json()["id"]
        _force_secret(gid, "crane")
        for w in guesses:
            client.post(f"/api/games/{gid}/guesses", json={"word": w})
    board = client.get("/api/leaderboard").json()
    assert [row["player"] for row in board] == ["fast", "slow"]


def test_unknown_game_is_404(client):
    assert client.get("/api/games/nope").status_code == 404
