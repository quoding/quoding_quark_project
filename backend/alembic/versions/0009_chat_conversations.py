"""chat_conversations / chat_messages — durable web chat history

Revision ID: 0009_chat_conversations
Revises: 0008_research_citation_count
Create Date: 2026-08-26

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_chat_conversations"
down_revision: str | None = "0008_research_citation_count"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from sqlalchemy import inspect

    bind = op.get_bind()
    existing = inspect(bind).get_table_names()

    if "chat_conversations" not in existing:
        op.create_table(
            "chat_conversations",
            sa.Column("session_id", sa.Text, primary_key=True),
            sa.Column("source", sa.Text, nullable=False, server_default="web"),
            sa.Column("title", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "chat_messages" not in existing:
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column(
                "session_id",
                sa.Text,
                sa.ForeignKey("chat_conversations.session_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.Text, nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("chat_conversations")
