"""Initial schema: games and their guesses.

Matches what the app used to create with Base.metadata.create_all, so databases made
that way are adopted by stamping this revision (see app/migrate.py).

Revision ID: 0001
Revises:
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "games",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("player", sa.String(length=32), nullable=False),
        sa.Column("secret", sa.String(length=5), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_games_player", "games", ["player"])
    op.create_index("ix_games_score", "games", ["score"])

    op.create_table(
        "guesses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.String(length=36), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("word", sa.String(length=5), nullable=False),
        sa.Column("marks", sa.JSON(), nullable=False),
    )
    op.create_index("ix_guesses_game_id", "guesses", ["game_id"])


def downgrade() -> None:
    op.drop_table("guesses")
    op.drop_table("games")
