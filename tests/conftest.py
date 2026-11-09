import os

# Use a throwaway database for the whole test run. This must happen before anything
# imports the app, which is why it lives here: pytest loads conftest.py first.
# Defaults to SQLite. Set TEST_DATABASE_URL to run the same tests against Postgres.
# (Deliberately not DATABASE_URL: the tests drop every table, so never point them at real data.)
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_wordgame.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Game  # noqa: E402


def reset_database() -> None:
    """Drop everything, including Alembic's bookkeeping table, so migrations start from zero."""
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")


@pytest.fixture()
def reset_db():
    """For tests that drive migrations themselves: call it to start from an empty database."""
    return reset_database


@pytest.fixture()
def client():
    reset_database()
    with TestClient(app) as c:  # app startup runs the migrations
        yield c


@pytest.fixture()
def force_secret():
    """Tests need a known answer, so this overwrites a game's random one."""

    def _force(game_id: str, word: str) -> None:
        with SessionLocal() as db:
            g = db.get(Game, game_id)
            g.secret = word
            db.commit()

    return _force
