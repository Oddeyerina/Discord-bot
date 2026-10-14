import asyncio
import logging
import re
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import GUILD_ID
from db import connect, decoded, settings
from utils.embeds import render


log = logging.getLogger(__name__)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def stats_values(guild: discord.Guild, role_counters: list[dict]) -> dict[str, str]:
    members = guild.members
    count = guild.premium_subscription_count or 0
    level = guild.premium_tier
    thresholds = (2, 7, 14)
    values = {
        "total_members": str(guild.member_count or len(members)),
        "human_members": str(sum(not member.bot for member in members)),
        "bot_members": str(sum(member.bot for member in members)),
        "online": str(sum(member.status != discord.Status.offline for member in members)),
        "in_voice": str(sum(member.voice is not None and member.voice.channel is not None for member in members)),
        "booster_count": str(len(guild.premium_subscribers)),
        "boost_count": str(count), "boost_level": str(level),
        "boosts_needed": str(max(0, thresholds[level] - count) if level < 3 else 0),
        "timestamp": f"<t:{int(datetime.now(timezone.utc).timestamp())}:R>",
    }
    for item in role_counters:
        key = slug(str(item.get("label", "")))
        role_id = item.get("role_id")
        if not key or not role_id:
            continue
        role = guild.get_role(int(role_id))
        amount = sum(role in member.roles for member in members) if role else 0
        values[f"role_count_{key}"] = str(amount)
        if key in {"artist", "artists"}:
            values["artist_count"] = str(amount)
        if key in {"verified", "verified_members"}:
            values["verified_count"] = str(amount)
    values.setdefault("artist_count", "0")
    values.setdefault("verified_count", "0")
    return values


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._loop: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self._loop is None or self._loop.done():
            self._loop = asyncio.create_task(self.update_loop())

    async def cog_unload(self) -> None:
        if self._loop is not None:
            self._loop.cancel()

    async def update_loop(self) -> None:
        while not self.bot.is_closed():
            try:
                config = settings("stats_config")
                if config and config["enabled"]:
                    last = datetime.fromisoformat(config["last_updated"]) if config["last_updated"] else None
                    if last is None or (datetime.now(timezone.utc) - last.replace(tzinfo=timezone.utc)).total_seconds() >= config["update_interval_seconds"]:
                        await self.post_stats()
            except Exception:
                log.exception("Stats update failed")
            await asyncio.sleep(60)

    async def post_stats(self, force: bool = False) -> None:
        async with self._lock:
            config = settings("stats_config")
            if not config or not config["channel_id"] or (not config["enabled"] and not force):
                log.warning("Stats are disabled or have no channel")
                return
            guild = self.bot.get_guild(GUILD_ID)
            channel = guild.get_channel(int(config["channel_id"])) if guild else None
            if guild is None or not isinstance(channel, discord.TextChannel):
                log.warning("Stats channel %s is unavailable", config["channel_id"])
                return
            values = stats_values(guild, decoded(config["role_counters_json"], []))
            embed = render(decoded(config["embed_json"], {}), guild, stats=values)
            message = None
            try:
                if config["message_id"]:
                    try:
                        message = await channel.fetch_message(int(config["message_id"]))
                        await message.edit(embed=embed)
                    except discord.NotFound:
                        message = None
                if message is None:
                    message = await channel.send(embed=embed)
            except discord.HTTPException:
                log.warning("Could not publish stats in channel %s", channel.id, exc_info=True)
                return
            with connect() as db:
                db.execute("UPDATE stats_config SET message_id = ?, last_updated = ? WHERE guild_id = ?",
                           (str(message.id), datetime.now(timezone.utc).isoformat(), str(GUILD_ID)))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Stats(bot))
