"""research_notes — Arxiv 연구조수(LangGraph) 아카이브

Revision ID: 0007_research_notes
Revises: 0006_reminder_escalated
Create Date: 2026-08-13

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_research_notes"
down_revision: str | None = "0006_reminder_escalated"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    if "research_notes" in inspect(bind).get_table_names():
        return  # already created by init_db

    op.create_table(
        "research_notes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("arxiv_id", sa.Text, nullable=False, unique=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("authors", sa.Text, nullable=False),
        sa.Column("summary_ko", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("keyword", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_research_notes_arxiv_id", "research_notes", ["arxiv_id"])


def downgrade() -> None:
    op.drop_index("ix_research_notes_arxiv_id", table_name="research_notes")
    op.drop_table("research_notes")
