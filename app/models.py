import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    player: Mapped[str] = mapped_column(String(32), index=True)
    secret: Mapped[str] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(10), default="playing")  # playing | won | lost
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

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
