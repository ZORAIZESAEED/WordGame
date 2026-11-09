"""The migrations and the SQLAlchemy models have to describe the same schema.

If someone changes a model without writing a migration, test_models_match_migrations
fails and lists the difference.
"""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.db import Base, engine
from app.migrate import alembic_config, upgrade_to_head
from app.models import Game

HEAD = ScriptDirectory.from_config(alembic_config()).get_current_head()


def _current_revision() -> str | None:
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def _tables() -> set[str]:
    return set(inspect(engine).get_table_names())


def test_models_match_migrations(reset_db):
    reset_db()
    upgrade_to_head(engine)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], f"Models and migrations differ; write a migration for: {diff}"


def test_upgrade_is_safe_to_run_twice(reset_db):
    reset_db()
    upgrade_to_head(engine)
    upgrade_to_head(engine)
    assert _current_revision() == HEAD


def test_downgrade_to_nothing_and_back(reset_db):
    reset_db()
    upgrade_to_head(engine)
    cfg = alembic_config()
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "base")
    assert _tables() <= {"alembic_version"}

    upgrade_to_head(engine)
    assert {"games", "guesses"} <= _tables()
    assert _current_revision() == HEAD


def test_adopts_a_database_created_before_migrations(reset_db):
    # The old app made its tables with create_all and had no alembic_version table.
    reset_db()
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO games (id, player, secret, status, score, created_at) "
                "VALUES ('old-game', 'early bird', 'crane', 'won', 600, CURRENT_TIMESTAMP)"
            )
        )

    upgrade_to_head(engine)

    assert _current_revision() == HEAD
    with engine.connect() as conn:
        assert conn.execute(text("SELECT player FROM games")).scalar_one() == "early bird"
    assert Game.__tablename__ in _tables()


def test_two_copies_starting_at_once_do_not_collide(reset_db):
    # Two containers booting together both see an empty database. Without a lock they'd
    # both try to CREATE TABLE and one would crash.
    import threading

    reset_db()
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def boot() -> None:
        barrier.wait()
        try:
            upgrade_to_head(engine)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=boot) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert errors == []
    assert _current_revision() == HEAD
