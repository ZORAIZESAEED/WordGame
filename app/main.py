from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import game as logic
from .db import Base, engine, get_db
from .models import Game, Guess

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fine for a small project. Swap for Alembic migrations later.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Word Game", version="0.1.0", lifespan=lifespan)


class NewGame(BaseModel):
    player: str = Field(min_length=1, max_length=32)


class GuessIn(BaseModel):
    word: str = Field(min_length=5, max_length=5)


class GuessOut(BaseModel):
    word: str
    marks: list[str]


class GameOut(BaseModel):
    id: str
    player: str
    status: str
    score: int
    attempts_used: int
    max_attempts: int
    guesses: list[GuessOut]
    answer: str | None = None  # only revealed once the game is over


class LeaderboardRow(BaseModel):
    player: str
    score: int


def _to_out(g: Game) -> GameOut:
    return GameOut(
        id=g.id,
        player=g.player,
        status=g.status,
        score=g.score,
        attempts_used=len(g.guesses),
        max_attempts=logic.MAX_ATTEMPTS,
        guesses=[GuessOut(word=x.word, marks=x.marks) for x in g.guesses],
        answer=g.secret if g.status != "playing" else None,
    )


def _get_game(db: Session, game_id: str) -> Game:
    g = db.get(Game, game_id)
    if g is None:
        raise HTTPException(404, "Game not found")
    return g


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/games", response_model=GameOut, status_code=201)
def new_game(body: NewGame, db: Session = Depends(get_db)):
    g = Game(player=body.player.strip(), secret=logic.pick_word())
    db.add(g)
    db.commit()
    return _to_out(g)


@app.get("/api/games/{game_id}", response_model=GameOut)
def get_game(game_id: str, db: Session = Depends(get_db)):
    return _to_out(_get_game(db, game_id))


@app.post("/api/games/{game_id}/guesses", response_model=GameOut)
def make_guess(game_id: str, body: GuessIn, db: Session = Depends(get_db)):
    g = _get_game(db, game_id)
    if g.status != "playing":
        raise HTTPException(409, "Game is already over")

    word = body.word.lower()
    if not logic.is_valid_guess(word):
        raise HTTPException(422, "Not in the word list")

    marks = logic.evaluate_guess(g.secret, word)
    g.guesses.append(Guess(word=word, marks=marks))
    used = len(g.guesses)

    if word == g.secret:
        g.status = "won"
        g.score = logic.score_for_win(used)
    elif used >= logic.MAX_ATTEMPTS:
        g.status = "lost"

    db.commit()
    return _to_out(g)


@app.get("/api/leaderboard", response_model=list[LeaderboardRow])
def leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 50))
    rows = db.execute(
        select(Game.player, Game.score)
        .where(Game.status == "won")
        .order_by(Game.score.desc(), Game.created_at.asc())
        .limit(limit)
    ).all()
    return [LeaderboardRow(player=p, score=s) for p, s in rows]


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
