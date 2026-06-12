"""Reminder model — persistent scheduled notifications."""
from __future__ import annotations

import datetime as _dt

from sqlalchemy import Boolean, DateTime, Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 발송 대상
    discord_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    discord_channel_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 내용
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 타이밍
    fire_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    cron_expr: Mapped[str | None] = mapped_column(Text, nullable=True)  # 반복 알림

    # 상태
    fired: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    snooze_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # 발송 후 일정 시간 반응(완료/스누즈)이 없어 DM으로 재알림했는지 여부
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
