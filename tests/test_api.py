import pytest


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_new_game_hides_the_answer(client):
    r = client.post("/api/games", json={"player": "zoraize"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "playing"
    assert body["answer"] is None
    assert body["max_attempts"] == 6


def test_win_flow_and_leaderboard(client, force_secret):
    gid = client.post("/api/games", json={"player": "zoraize"}).json()["id"]
    force_secret(gid, "crane")

    r = client.post(f"/api/games/{gid}/guesses", json={"word": "slate"})
    assert r.status_code == 200 and r.json()["status"] == "playing"

    r = client.post(f"/api/games/{gid}/guesses", json={"word": "crane"})
    body = r.json()
    assert body["status"] == "won"
    assert body["score"] == 500  # won on attempt 2
    assert body["answer"] == "crane"

    board = client.get("/api/leaderboard").json()
    assert board == [{"player": "zoraize", "score": 500}]


def test_lose_after_six_wrong_guesses(client, force_secret):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    force_secret(gid, "crane")
    for _ in range(6):
        r = client.post(f"/api/games/{gid}/guesses", json={"word": "about"})
    assert r.json()["status"] == "lost"
    assert r.json()["answer"] == "crane"
    assert client.get("/api/leaderboard").json() == []


def test_cannot_guess_after_game_over(client, force_secret):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    force_secret(gid, "crane")
    client.post(f"/api/games/{gid}/guesses", json={"word": "crane"})
    r = client.post(f"/api/games/{gid}/guesses", json={"word": "about"})
    assert r.status_code == 409


def test_rejects_words_not_in_list(client):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    r = client.post(f"/api/games/{gid}/guesses", json={"word": "zzzzz"})
    assert r.status_code == 422


@pytest.mark.parametrize("word", ["cr4ne", "cra e", "crané", "cran", "cranes", ""])
def test_rejects_guesses_that_are_not_five_letters(client, word):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    r = client.post(f"/api/games/{gid}/guesses", json={"word": word})
    assert r.status_code == 422
    assert r.json()["detail"][0]["msg"] == "Guesses must be five letters, A to Z"
    # A rejected guess doesn't use up an attempt.
    assert client.get(f"/api/games/{gid}").json()["attempts_used"] == 0


def test_guess_is_trimmed(client, force_secret):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    force_secret(gid, "crane")
    body = client.post(f"/api/games/{gid}/guesses", json={"word": "  crane "}).json()
    assert body["status"] == "won"


def test_accepts_less_common_dictionary_words(client, force_secret):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    force_secret(gid, "crane")
    r = client.post(f"/api/games/{gid}/guesses", json={"word": "fjord"})
    assert r.status_code == 200


def test_player_name_is_trimmed(client):
    r = client.post("/api/games", json={"player": "  zoraize  "})
    assert r.status_code == 201
    assert r.json()["player"] == "zoraize"


@pytest.mark.parametrize("name", ["", "   ", "x" * 33])
def test_rejects_bad_player_names(client, name):
    assert client.post("/api/games", json={"player": name}).status_code == 422


def test_guess_is_case_insensitive(client, force_secret):
    gid = client.post("/api/games", json={"player": "p"}).json()["id"]
    force_secret(gid, "crane")
    body = client.post(f"/api/games/{gid}/guesses", json={"word": "CRANE"}).json()
    assert body["status"] == "won"
    assert body["guesses"][0]["word"] == "crane"


def test_leaderboard_orders_by_score(client, force_secret):
    for player, guesses in [("slow", ["slate", "crane"]), ("fast", ["crane"])]:
        gid = client.post("/api/games", json={"player": player}).json()["id"]
        force_secret(gid, "crane")
        for w in guesses:
            client.post(f"/api/games/{gid}/guesses", json={"word": w})
    board = client.get("/api/leaderboard").json()
    assert [row["player"] for row in board] == ["fast", "slow"]


def test_unknown_game_is_404(client):
    assert client.get("/api/games/nope").status_code == 404
