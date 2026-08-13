"""QUARK Discord 활용도 확장 — /quark 조회 커맨드, 위험 동작 버튼 확인, 메시지 컨텍스트 메뉴."""
from __future__ import annotations

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.agenda import Todo

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")
_REBOOT_KEYWORDS = ("재부팅", "리부팅", "리붓", "reboot")


# ── 위험 동작 확인 버튼 (재부팅) ─────────────────────────────────────────────────

class RebootConfirmView(discord.ui.View):
    """N100 재부팅 전 확인 버튼 — 30초 타임아웃, 요청자 본인만 조작 가능."""

    def __init__(self, requester_id: int) -> None:
        super().__init__(timeout=30)
        self.requester_id = requester_id

    async def _authorize(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message("본인이 요청한 동작만 확인할 수 있어.", ephemeral=True)
            return False
        return True

    def _disable_all(self) -> None:
        for item in self.children:
            item.disabled = True  # type: ignore[attr-defined]

    @discord.ui.button(label="재부팅 확인", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._authorize(interaction):
            return
        await interaction.response.defer()
        from app.services.host_helper import reboot_host

        ok = await reboot_host()
        self._disable_all()
        await interaction.edit_original_response(
            content="✅ N100 서버에 재부팅 명령을 보냈어." if ok else "❌ 재부팅 실패 — host-helper에 연결 못 했어.",
            view=self,
        )
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await self._authorize(interaction):
            return
        self._disable_all()
        await interaction.response.edit_message(content="취소했어.", view=self)
        self.stop()

    async def on_timeout(self) -> None:
        self._disable_all()


def is_reboot_request(content: str) -> bool:
    return any(kw in content for kw in _REBOOT_KEYWORDS)


# ── /quark 조회 커맨드 ───────────────────────────────────────────────────────

class QuarkCommandsCog(commands.Cog, name="QuarkCommands"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="할일로 등록",
            callback=self.add_as_todo,
        )
        bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    quark_group = app_commands.Group(name="quark", description="자주 쓰는 조회를 즉답으로 받기")

    @quark_group.command(name="schedule", description="오늘 일정을 조회합니다.")
    async def schedule(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        from app.services import google_calendar

        today = date.today()
        day_start = datetime(today.year, today.month, today.day, 0, 0, 0).isoformat() + "+09:00"
        day_end = datetime(today.year, today.month, today.day, 23, 59, 59).isoformat() + "+09:00"
        events = await google_calendar.list_events(day_start, day_end)

        if not events:
            await interaction.followup.send(f"{today.isoformat()} 일정 없음", ephemeral=True)
            return

        lines = []
        for e in events:
            when = "종일" if e["all_day"] else (e["start"][11:16] if len(e["start"]) >= 16 else e["start"])
            lines.append(f"`{when}` {e['title']}")
        embed = discord.Embed(title=f"📅 {today.isoformat()} 일정", description="\n".join(lines), color=discord.Color.blue())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @quark_group.command(name="todos", description="미완료 할 일을 조회합니다.")
    async def todos(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(Todo).where(Todo.done.is_(False)).order_by(Todo.created_at))
            pending = res.scalars().all()

        if not pending:
            await interaction.followup.send("미완료 할 일 없음", ephemeral=True)
            return

        lines = [f"`{t.id}` {t.text}" for t in pending]
        embed = discord.Embed(title="✅ 미완료 할 일", description="\n".join(lines), color=discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @quark_group.command(name="weather", description="현재 날씨를 조회합니다.")
    async def weather(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        from app.services.weather import get_current_weather

        data = await get_current_weather()
        if "error" in data:
            await interaction.followup.send("날씨 조회 실패 — 잠시 후 다시 시도해줘.", ephemeral=True)
            return

        await interaction.followup.send(
            f"🌤️ {data['city']}: {data['label']}, 현재 {data['temp']}°C "
            f"(최고 {data['hi']}°C / 최저 {data['lo']}°C), "
            f"미세먼지 {data['pm25']}㎍/㎥ ({data['aqi_grade']})",
            ephemeral=True,
        )

    # ── 컨텍스트 메뉴: 메시지 우클릭 → 할일로 등록 ────────────────────────────────

    async def add_as_todo(self, interaction: discord.Interaction, message: discord.Message) -> None:
        text = message.content.strip()
        if not text:
            await interaction.response.send_message("빈 메시지는 할일로 등록할 수 없어.", ephemeral=True)
            return

        async with AsyncSessionLocal() as db:
            todo = Todo(text=text)
            db.add(todo)
            await db.flush()
            await db.commit()
            todo_id = todo.id

        await interaction.response.send_message(f"✅ 할일로 등록했어 (`{todo_id}`): {text[:100]}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(QuarkCommandsCog(bot))
