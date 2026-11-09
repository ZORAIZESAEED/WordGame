"""Play one round against a running server and check the responses make sense.

Usage: python scripts/smoke_test.py [base_url]   (default http://localhost:8000)

Standard library only, so it runs anywhere without installing anything. CI uses it
against the docker compose stack, which means it exercises the real Postgres path.
"""

import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")


def call(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            raw = res.read()
            ctype = res.headers.get("Content-Type", "")
            return res.status, json.loads(raw) if "json" in ctype else raw.decode()
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")
    except urllib.error.URLError as e:
        sys.exit(f"FAIL can't reach {BASE}{path}: {e.reason}. Is the server running?")


def check(ok: bool, what: str) -> None:
    print(("PASS " if ok else "FAIL ") + what)
    if not ok:
        sys.exit(1)


status, body = call("GET", "/health")
check(status == 200 and body == {"status": "ok"}, "health check")

status, page = call("GET", "/")
check(status == 200 and "<html" in page.lower(), "frontend is served")

status, game = call("POST", "/api/games", {"player": "smoke-test"})
check(status == 201 and game["status"] == "playing", "start a game")
check(game["answer"] is None, "answer stays hidden while playing")

# Before the real guess: "crane" is a possible answer, and a won game returns 409 instead.
status, err = call("POST", f"/api/games/{game['id']}/guesses", {"word": "zzzzz"})
check(status == 422, "unknown words are rejected")

status, game = call("POST", f"/api/games/{game['id']}/guesses", {"word": "crane"})
check(status == 200 and len(game["guesses"]) == 1, "make a guess")
check(len(game["guesses"][0]["marks"]) == 5, "guess is marked letter by letter")

status, again = call("GET", f"/api/games/{game['id']}")
check(status == 200 and again["guesses"] == game["guesses"], "game is saved in the database")

status, board = call("GET", "/api/leaderboard")
check(status == 200 and isinstance(board, list), "leaderboard responds")

print("Smoke test passed against " + BASE)
