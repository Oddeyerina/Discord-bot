import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import GUILD_ID
from db import connect, decoded, one
from utils.embeds import render

log = logging.getLogger(__name__)


class Sticky(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.locks: dict[str, asyncio.Lock] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.guild.id != GUILD_ID or message.author.bot:
            return
        if one("SELECT id FROM sticky_channels WHERE guild_id = ? AND channel_id = ? AND enabled = 1",
               (str(GUILD_ID), str(message.channel.id))):
            try:
                await self.post_sticky(str(message.channel.id))
            except (discord.Forbidden, discord.HTTPException, ValueError):
                log.exception("Could not refresh sticky in channel %s", message.channel.id)

    async def post_sticky(self, channel_id: str, force: bool = False) -> None:
        async with self.locks.setdefault(channel_id, asyncio.Lock()):
            row = one("SELECT * FROM sticky_channels WHERE guild_id = ? AND channel_id = ?",
                      (str(GUILD_ID), channel_id))
            if row is None or (not row["enabled"] and not force):
                return
            now = datetime.now(timezone.utc)
            if not force and row["last_sticky_at"]:
                last = datetime.fromisoformat(row["last_sticky_at"]).replace(tzinfo=timezone.utc)
                if (now - last).total_seconds() < row["cooldown_seconds"]:
                    return
            guild = self.bot.get_guild(GUILD_ID)
            channel = guild.get_channel(int(channel_id)) if guild else None
            if not isinstance(channel, discord.TextChannel):
                raise ValueError("Sticky channel unavailable")
            if row["sticky_message_id"]:
                try:
                    old = await channel.fetch_message(int(row["sticky_message_id"]))
                    await old.delete()
                except discord.NotFound:
                    pass
            role = guild.get_role(int(row["role_id"])) if row["role_id"] else None

            if role:
                if embed.description:
                    embed.description = embed.description + "\n\n" + role.mention
                else:
                    embed.description = role.mention
                allowed = discord.AllowedMentions(everyone=False, users=False, roles=[role])
            else:
                allowed = discord.AllowedMentions.none()

            message = await channel.send(embed=embed, allowed_mentions=allowed)

            with connect() as db:
                db.execute("UPDATE sticky_channels SET sticky_message_id = ?, last_sticky_at = ? WHERE id = ?",
                           (str(message.id), now.isoformat(), row["id"]))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sticky(bot))
