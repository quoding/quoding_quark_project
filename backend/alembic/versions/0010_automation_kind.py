"""automations.kind / automations.slug — distinguish system automations from user macros

Revision ID: 0010_automation_kind
Revises: 0009_chat_conversations
Create Date: 2026-08-29

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_automation_kind"
down_revision: str | None = "0009_chat_conversations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    columns = {c["name"] for c in inspect(bind).get_columns("automations")}

    if "kind" not in columns:
        op.add_column(
            "automations",
            sa.Column("kind", sa.Text, nullable=False, server_default="macro"),
        )
    if "slug" not in columns:
        op.add_column("automations", sa.Column("slug", sa.Text, nullable=True))
        op.create_unique_constraint("uq_automations_slug", "automations", ["slug"])


def downgrade() -> None:
    op.drop_constraint("uq_automations_slug", "automations", type_="unique")
    op.drop_column("automations", "slug")
    op.drop_column("automations", "kind")
