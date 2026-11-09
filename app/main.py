from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, StringConstraints, field_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import daily
from . import game as logic
from .db import engine, get_db
from .migrate import upgrade_to_head
from .models import Game, Guess

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    upgrade_to_head(engine)
    yield


app = FastAPI(title="Word Game", version="0.1.0", lifespan=lifespan)


class NewGame(BaseModel):
    # Strip first, then check the length, so "   " is rejected instead of saved as "".
    player: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class GuessIn(BaseModel):
    word: str

    @field_validator("word")
    @classmethod
    def five_letters(cls, v: str) -> str:
        v = v.strip().lower()
        if len(v) != logic.WORD_LENGTH or not (v.isascii() and v.isalpha()):
            # Custom error type so the message reaches the player without a "Value error," prefix.
            raise PydanticCustomError("five_letters", "Guesses must be five letters, A to Z")
        return v


class GuessOut(BaseModel):
    word: str
    marks: list[str]


class GameOut(BaseModel):
    id: str
    player: str
    mode: str  # practice | daily
    daily_number: int | None = None  # "Daily #12", for daily games
    status: str
    score: int
    attempts_used: int
    max_attempts: int
    guesses: list[GuessOut]
    answer: str | None = None  # only revealed once the game is over


class LeaderboardRow(BaseModel):
    player: str
    score: int


class DailyInfo(BaseModel):
    date: date
    number: int


def _to_out(g: Game) -> GameOut:
    return GameOut(
        id=g.id,
        player=g.player,
        mode=g.mode,
        daily_number=daily.puzzle_number(g.daily_date) if g.daily_date else None,
        status=g.status,
        score=g.score,
        attempts_used=len(g.guesses),
        max_attempts=logic.MAX_ATTEMPTS,
        guesses=[GuessOut(word=x.word, marks=x.marks) for x in g.guesses],
        answer=g.secret if g.status != "playing" else None,
    )


def _get_game(db: Session, game_id: str, *, lock: bool = False) -> Game:
    # lock=True takes a row lock (SELECT ... FOR UPDATE on Postgres) that's held until
    # commit, so a second request for the same game waits and then sees the first one's guess.
    g = db.get(Game, game_id, with_for_update=lock)
    if g is None:
        raise HTTPException(404, "Game not found")
    return g


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/games", response_model=GameOut, status_code=201)
def new_game(body: NewGame, db: Session = Depends(get_db)):
    g = Game(player=body.player, secret=logic.pick_word())
    db.add(g)
    db.commit()
    return _to_out(g)


def _find_daily(db: Session, player: str, day: date) -> Game | None:
    return db.scalars(
        select(Game).where(Game.player == player, Game.daily_date == day)
    ).one_or_none()


@app.get("/api/daily", response_model=DailyInfo)
def daily_info():
    """Which daily puzzle is live right now. Never includes the word."""
    day = daily.today()
    return DailyInfo(date=day, number=daily.puzzle_number(day))


@app.post("/api/daily", response_model=GameOut, status_code=201)
def start_daily(body: NewGame, response: Response, db: Session = Depends(get_db)):
    """Start today's daily game, or carry on with it if this player already started one."""
    day = daily.today()
    existing = _find_daily(db, body.player, day)
    if existing is not None:
        response.status_code = 200
        return _to_out(existing)

    g = Game(player=body.player, secret=daily.word_for(day), mode="daily", daily_date=day)
    db.add(g)
    try:
        db.commit()
    except IntegrityError:
        # Another request for the same player and day got there first (the unique
        # constraint stopped a second game), so hand back that one.
        db.rollback()
        response.status_code = 200
        return _to_out(_find_daily(db, body.player, day))
    return _to_out(g)


@app.get("/api/daily/leaderboard", response_model=list[LeaderboardRow])
def daily_leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    """Today's daily winners: fewest guesses first, then whoever finished earliest."""
    limit = max(1, min(limit, 50))
    rows = db.execute(
        select(Game.player, Game.score)
        .where(Game.daily_date == daily.today(), Game.status == "won")
        .order_by(Game.score.desc(), Game.created_at.asc())
        .limit(limit)
    ).all()
    return [LeaderboardRow(player=p, score=s) for p, s in rows]


@app.get("/api/games/{game_id}", response_model=GameOut)
def get_game(game_id: str, db: Session = Depends(get_db)):
    return _to_out(_get_game(db, game_id))


@app.post("/api/games/{game_id}/guesses", response_model=GameOut)
def make_guess(game_id: str, body: GuessIn, db: Session = Depends(get_db)):
    # Lock first: everything below reads the game and writes back based on what it saw.
    g = _get_game(db, game_id, lock=True)
    if g.status != "playing":
        raise HTTPException(409, "Game is already over")

    word = body.word  # already trimmed and lowercased by GuessIn
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
