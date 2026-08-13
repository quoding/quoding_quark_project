"""research_notes.citation_count — Semantic Scholar 인용수 보강

Revision ID: 0008_research_citation_count
Revises: 0007_research_notes
Create Date: 2026-08-13

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_research_citation_count"
down_revision: str | None = "0007_research_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns("research_notes")}
    if "citation_count" in cols:
        return

    op.add_column(
        "research_notes",
        sa.Column("citation_count", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("research_notes", "citation_count")
