"""Bring the database schema up to date with Alembic. Runs when the app starts."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

# The revision that matches the tables the app used to make with create_all().
BASELINE = "0001"

# Any fixed number works; it just has to be the same for every copy of the app.
_PG_LOCK_ID = 727_455_001

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return cfg


def upgrade_to_head(engine: Engine) -> None:
    """Apply any pending migrations, all in one transaction.

    - On Postgres, an advisory lock makes a second copy of the app (another container, a
      rolling deploy) wait instead of running the same migrations at the same time. On
      SQLite, BEGIN IMMEDIATE (see app/db.py) does the same job.
    - A database created before migrations existed has the tables but no alembic_version
      table. It gets stamped at the baseline instead of failing on "table already exists".
    """
    cfg = alembic_config()
    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.exec_driver_sql(f"SELECT pg_advisory_xact_lock({_PG_LOCK_ID})")

        cfg.attributes["connection"] = conn
        tables = set(inspect(conn).get_table_names())
        if "games" in tables and "alembic_version" not in tables:
            command.stamp(cfg, BASELINE)
        command.upgrade(cfg, "head")
