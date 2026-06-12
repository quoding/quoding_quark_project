"""reminders.escalated — DM escalation flag

Revision ID: 0006_reminder_escalated
Revises: 0005_drop_scheduled_events
Create Date: 2026-06-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_reminder_escalated"
down_revision: str | None = "0005_drop_scheduled_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("reminders")}
    if "escalated" in cols:
        return

    op.add_column(
        "reminders",
        sa.Column("escalated", sa.Boolean, nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("reminders", "escalated")
