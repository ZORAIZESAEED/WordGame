"""Alembic environment.

Runs against a connection handed over by app/migrate.py when the app starts, or against
the app's own engine when you use the `alembic` command line.
"""

from alembic import context

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.db import Base, engine

target_metadata = Base.metadata


def _configure(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        # SQLite can't ALTER most things; batch mode rebuilds the table instead.
        render_as_batch=connection.dialect.name == "sqlite",
    )


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _configure(connection)
        with context.begin_transaction():
            context.run_migrations()
        return

    with engine.connect() as connection:
        _configure(connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline (--sql) mode isn't set up for this project.")
run_migrations_online()
