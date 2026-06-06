"""reminders table

Revision ID: 0004_reminders
Revises: 0003_health
Create Date: 2026-06-06
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_reminders"
down_revision: str | None = "0003_health"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    if "reminders" in inspect(bind).get_table_names():
        return

    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("discord_user_id", sa.Text, nullable=False),
        sa.Column("discord_channel_id", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("fire_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("cron_expr", sa.Text, nullable=True),
        sa.Column("fired", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("done", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("snooze_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("reminders")
