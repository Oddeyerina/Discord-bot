import asyncio
import logging
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID
from db import all_rows, connect, decoded, settings
from utils.embeds import render

log = logging.getLogger(__name__)
MONTH_NAMES = ("January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December")


class Remembering(commands.Cog):
    birthday = app_commands.Group(name="birthday", description="Manage your recurring dates")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.daily_task: asyncio.Task | None = None

    async def cog_load(self) -> None:
        self.daily_task = asyncio.create_task(self.daily_loop())

    async def cog_unload(self) -> None:
        if self.daily_task:
            self.daily_task.cancel()

    @birthday.command(name="set", description="Save a birthday or recurring date")
    @app_commands.describe(day="Day of the month (1-31)", month="Month of the date",
                           label="Label, e.g. 'Birthday' or 'Anniversary'",
                           year="Optional year (for age calculation)")
    @app_commands.choices(month=[app_commands.Choice(name=name, value=index)
                                 for index, name in enumerate(MONTH_NAMES, 1)])
    async def set_date(self, interaction: discord.Interaction, day: app_commands.Range[int, 1, 31],
                       month: int, label: str = "Birthday",
                       year: app_commands.Range[int, 1900, 2100] | None = None) -> None:
        try:
            date(year or 2000, month, day)
        except ValueError:
            await interaction.response.send_message("Enter a valid calendar date.", ephemeral=True)
            return
        if year is not None and (year < 1900 or year > datetime.now(timezone.utc).year):
            await interaction.response.send_message("The year must be between 1900 and the current year.", ephemeral=True)
            return
        label = label.strip()[:100]
        if not label:
            await interaction.response.send_message("Enter a label.", ephemeral=True)
            return
        with connect() as db:
            db.execute("INSERT INTO remembered_dates (guild_id, user_id, date_day, date_month, date_year, label, saved_at) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(guild_id, user_id, label) DO UPDATE SET "
                       "date_day = excluded.date_day, date_month = excluded.date_month, "
                       "date_year = excluded.date_year, saved_at = excluded.saved_at",
                       (str(GUILD_ID), str(interaction.user.id), day, month, year, label,
                        datetime.now(timezone.utc).isoformat()))
        year_part = f" {year}" if year is not None else ""
        await interaction.response.send_message(
            f"Saved **{label}** for {day:02d}. {MONTH_NAMES[month - 1]}{year_part}.", ephemeral=True)

    @birthday.command(name="remove", description="Remove one of your recurring dates")
    @app_commands.describe(label="Label of the date to remove")
    async def remove_date(self, interaction: discord.Interaction, label: str = "Birthday") -> None:
        with connect() as db:
            removed = db.execute(
                "DELETE FROM remembered_dates WHERE guild_id = ? AND user_id = ? AND label = ?",
                (str(GUILD_ID), str(interaction.user.id), label)).rowcount
        await interaction.response.send_message(
            f"Removed **{label}**." if removed else f"No saved date has the label **{label}**.", ephemeral=True)

    @birthday.command(name="list", description="List your saved recurring dates")
    async def list_dates(self, interaction: discord.Interaction) -> None:
        rows = all_rows("SELECT * FROM remembered_dates WHERE guild_id = ? AND user_id = ? ORDER BY date_month, date_day",
                        (str(GUILD_ID), str(interaction.user.id)))
        if not rows:
            await interaction.response.send_message("You have no saved dates.", ephemeral=True)
            return
        lines = [
            f"• **{row['label']}**: {row['date_day']:02d}. {MONTH_NAMES[row['date_month'] - 1]}"
            + (f" {row['date_year']}" if row["date_year"] else "")
            for row in rows
        ]
        await interaction.response.send_message("Your saved dates:\n" + "\n".join(lines), ephemeral=True)

    async def daily_loop(self) -> None:
        await self.bot.wait_until_ready()
        if datetime.now(timezone.utc).hour >= 8:
            try:
                await self.announce_today()
            except Exception:
                log.exception("Remembered date catch-up check failed")
        while not self.bot.is_closed():
            now = datetime.now(timezone.utc)
            next_run = datetime.combine(now.date(), time(8, tzinfo=timezone.utc))
            if next_run <= now:
                next_run = datetime.combine(date.fromordinal(now.date().toordinal() + 1),
                                            time(8, tzinfo=timezone.utc))
            await asyncio.sleep((next_run - now).total_seconds())
            try:
                await self.announce_today()
            except Exception:
                log.exception("Remembered date check failed")

    async def announce_today(self) -> None:
        config = settings("remembered_dates_config")
        if not config or not config["enabled"] or not config["channel_id"]:
            return
        guild = self.bot.get_guild(GUILD_ID)
        channel = guild.get_channel(int(config["channel_id"])) if guild else None
        if not isinstance(channel, discord.TextChannel):
            return
        local_today = datetime.now(ZoneInfo(config["timezone"])).date()
        rows = all_rows("SELECT * FROM remembered_dates WHERE guild_id = ? AND date_month = ? AND date_day = ?",
                        (str(GUILD_ID), local_today.month, local_today.day))
        for row in rows:
            user = guild.get_member(int(row["user_id"])) if guild else None
            if user is None:
                try:
                    user = await guild.fetch_member(int(row["user_id"])) if guild else None
                except discord.HTTPException:
                    user = None
            if user is None:
                continue
            with connect() as db:
                inserted = db.execute("INSERT OR IGNORE INTO remembered_announcements "
                                      "(guild_id, date_id, local_date) VALUES (?, ?, ?)",
                                      (str(GUILD_ID), row["id"], local_today.isoformat())).rowcount
            if not inserted:
                continue
            age = local_today.year - row["date_year"] if row["date_year"] else None
            try:
                await channel.send(embed=render(decoded(config["announcement_embed_json"], {}),
                                                guild, user, label=row["label"], age=age))
            except discord.HTTPException:
                with connect() as db:
                    db.execute("DELETE FROM remembered_announcements WHERE date_id = ? AND local_date = ?",
                               (row["id"], local_today.isoformat()))
                log.exception("Could not announce date %s", row["id"])


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Remembering(bot), guild=discord.Object(id=GUILD_ID))
