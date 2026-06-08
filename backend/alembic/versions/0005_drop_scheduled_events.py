"""drop scheduled_events — events now proxied through Google Calendar

Revision ID: 0005_drop_scheduled_events
Revises: 0004_reminders
Create Date: 2026-06-08

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_drop_scheduled_events"
down_revision: str | None = "0004_reminders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_scheduled_events_scheduled_at", table_name="scheduled_events")
    op.drop_table("scheduled_events")


def downgrade() -> None:
    op.create_table(
        "scheduled_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tag", sa.Text(), nullable=False, server_default="개인"),
        sa.Column("done", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scheduled_events_scheduled_at", "scheduled_events", ["scheduled_at"])
