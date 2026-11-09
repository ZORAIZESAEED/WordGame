import uuid
from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Game(Base):
    __tablename__ = "games"
    # One daily game per player name per day. Practice games have no daily_date, and NULLs
    # never clash in a unique constraint, so practice stays unlimited.
    __table_args__ = (UniqueConstraint("player", "daily_date", name="uq_games_player_daily_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    player: Mapped[str] = mapped_column(String(32), index=True)
    secret: Mapped[str] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(10), default="playing")  # playing | won | lost
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    mode: Mapped[str] = mapped_column(  # practice | daily
        String(10), default="practice", server_default="practice"
    )
    daily_date: Mapped[date | None] = mapped_column(Date, index=True)

    guesses: Mapped[list["Guess"]] = relationship(
        back_populates="game", order_by="Guess.id", cascade="all, delete-orphan"
    )


class Guess(Base):
    __tablename__ = "guesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), index=True)
    word: Mapped[str] = mapped_column(String(5))
    marks: Mapped[list] = mapped_column(JSON)

    game: Mapped[Game] = relationship(back_populates="guesses")
