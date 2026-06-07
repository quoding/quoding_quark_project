"""Discord Reminder Cog — /remind, /reminders + DynamicItem snooze buttons."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.services import reminder_service

logger = logging.getLogger(__name__)
settings = get_settings()

_SNOOZE_OPTIONS = [5, 10, 30, 60]  # minutes


# ── Persistent snooze/done view ───────────────────────────────────────────────

class ReminderView(discord.ui.View):
    """Persistent view attached to each reminder message.

    Uses custom_id encoding so buttons survive bot restarts without DB lookup.
    Pattern:  reminder:snooze:<id>:<minutes>  |  reminder:done:<id>
    """

    def __init__(self, reminder_id: int) -> None:
        super().__init__(timeout=None)
        self.message: discord.Message | None = None

        for minutes in _SNOOZE_OPTIONS:
            self.add_item(_SnoozeButton(reminder_id=reminder_id, minutes=minutes))
        self.add_item(_DoneButton(reminder_id=reminder_id))


class _SnoozeButton(discord.ui.DynamicItem[discord.ui.Button], template=r"reminder:snooze:(?P<id>\d+):(?P<min>\d+)"):
    """Snooze button — encodes id and minutes in custom_id."""

    def __init__(self, *, reminder_id: int, minutes: int) -> None:
        super().__init__(
            discord.ui.Button(
                label=f"{minutes}분 후",
                style=discord.ButtonStyle.secondary,
                custom_id=f"reminder:snooze:{reminder_id}:{minutes}",
                emoji="💤",
            )
        )
        self.reminder_id = reminder_id
        self.minutes = minutes

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Button,
        match: __import__("re").Match,
    ) -> "_SnoozeButton":
        return cls(reminder_id=int(match["id"]), minutes=int(match["min"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        async with AsyncSessionLocal() as db:
            r = await reminder_service.snooze_reminder(db, self.reminder_id, self.minutes)

        if r is None:
            await interaction.followup.send("알림을 찾을 수 없어요.", ephemeral=True)
            return

        fire_local = r.fire_at.astimezone(
            __import__("zoneinfo").ZoneInfo("Asia/Seoul")
        )
        await interaction.followup.send(
            f"💤 {self.minutes}분 후인 {fire_local.strftime('%H:%M')}에 다시 알려드릴게요!",
            ephemeral=True,
        )
        if interaction.message:
            await interaction.message.edit(view=None)


class _DoneButton(discord.ui.DynamicItem[discord.ui.Button], template=r"reminder:done:(?P<id>\d+)"):
    """Done button — marks reminder as completed."""

    def __init__(self, *, reminder_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label="완료",
                style=discord.ButtonStyle.success,
                custom_id=f"reminder:done:{reminder_id}",
                emoji="✅",
            )
        )
        self.reminder_id = reminder_id

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Button,
        match: __import__("re").Match,
    ) -> "_DoneButton":
        return cls(reminder_id=int(match["id"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        async with AsyncSessionLocal() as db:
            await reminder_service.mark_done(db, self.reminder_id)
        await interaction.followup.send("✅ 알림을 완료했어요!", ephemeral=True)
        if interaction.message:
            await interaction.message.edit(view=None)


# ── Reminder Cog ──────────────────────────────────────────────────────────────

class ReminderCog(commands.Cog, name="Reminder"):
    """Slash commands for scheduling and managing reminders."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Register DynamicItem handlers so buttons survive restarts
        bot.add_dynamic_items(_SnoozeButton, _DoneButton)

    # /remind <time> <message>
    @app_commands.command(name="remind", description="알림을 설정합니다. 예: /remind 매일 오전 9시 약먹기")
    @app_commands.describe(
        when="언제 알릴까요? (예: 30분 후, 매일 오전 9시, 내일 오후 3시)",
        message="알림 내용",
    )
    async def remind(
        self,
        interaction: discord.Interaction,
        when: str,
        message: str,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        result = await reminder_service.parse_reminder_time(when)

        if result.get("error") or result.get("fire_at") is None:
            err = result.get("error", "시간을 이해하지 못했어요.")
            await interaction.followup.send(
                f"❌ 시간 파싱 실패: {err}\n"
                "예시: `30분 후`, `내일 오후 3시`, `매일 오전 9시`",
                ephemeral=True,
            )
            return

        fire_at: datetime = result["fire_at"]
        cron_expr: str | None = result.get("cron_expr")

        channel_id = str(interaction.channel_id) if interaction.channel_id else None

        async with AsyncSessionLocal() as db:
            r = await reminder_service.create_reminder(
                db,
                discord_user_id=str(interaction.user.id),
                discord_channel_id=channel_id,
                content=message,
                fire_at=fire_at,
                cron_expr=cron_expr,
            )

        fire_local = fire_at.astimezone(__import__("zoneinfo").ZoneInfo("Asia/Seoul"))
        recurrence_note = f" (반복: `{cron_expr}`)" if cron_expr else ""

        await interaction.followup.send(
            f"⏰ **{fire_local.strftime('%Y-%m-%d %H:%M')}**에 알려드릴게요!{recurrence_note}\n"
            f"> {message}\n"
            f"*(알림 ID: `{r.id}`)*",
            ephemeral=True,
        )

    # /reminders  —  subcommand group
    reminders_group = app_commands.Group(name="reminders", description="알림 관리")

    @reminders_group.command(name="list", description="등록된 알림 목록을 봅니다.")
    async def reminders_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as db:
            reminders = await reminder_service.list_reminders(db, str(interaction.user.id))

        if not reminders:
            await interaction.followup.send("등록된 알림이 없어요.", ephemeral=True)
            return

        tz = __import__("zoneinfo").ZoneInfo("Asia/Seoul")
        lines = []
        for r in reminders:
            fire_str = r.fire_at.astimezone(tz).strftime("%m/%d %H:%M")
            recur = f" 🔁`{r.cron_expr}`" if r.cron_expr else ""
            lines.append(f"`{r.id}` | {fire_str}{recur} — {r.content[:50]}")

        embed = discord.Embed(
            title="📋 예정된 알림",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @reminders_group.command(name="delete", description="알림을 삭제합니다.")
    @app_commands.describe(reminder_id="삭제할 알림의 ID")
    async def reminders_delete(self, interaction: discord.Interaction, reminder_id: int) -> None:
        await interaction.response.defer(ephemeral=True)

        async with AsyncSessionLocal() as db:
            deleted = await reminder_service.delete_reminder(
                db, reminder_id, str(interaction.user.id)
            )

        if deleted:
            await interaction.followup.send(f"✅ 알림 `{reminder_id}`을 삭제했어요.", ephemeral=True)
        else:
            await interaction.followup.send("❌ 알림을 찾을 수 없거나 권한이 없어요.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderCog(bot))
