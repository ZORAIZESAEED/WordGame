"""Daily challenge: a mode for every game, and the day a daily game belongs to.

Existing games become practice games. One daily game per player name per day is
enforced by a unique constraint, so two simultaneous "start daily" requests can't
create two games.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table: SQLite can't add constraints with ALTER, so Alembic rebuilds the
    # table there. On Postgres these are ordinary ALTER TABLE statements.
    with op.batch_alter_table("games") as batch_op:
        batch_op.add_column(
            sa.Column("mode", sa.String(length=10), server_default="practice", nullable=False)
        )
        batch_op.add_column(sa.Column("daily_date", sa.Date(), nullable=True))
        batch_op.create_index("ix_games_daily_date", ["daily_date"])
        batch_op.create_unique_constraint("uq_games_player_daily_date", ["player", "daily_date"])


def downgrade() -> None:
    with op.batch_alter_table("games") as batch_op:
        batch_op.drop_constraint("uq_games_player_daily_date", type_="unique")
        batch_op.drop_index("ix_games_daily_date")
        batch_op.drop_column("daily_date")
        batch_op.drop_column("mode")
