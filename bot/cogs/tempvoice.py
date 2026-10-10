import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import GUILD_ID
from db import connect, one, settings

log = logging.getLogger(__name__)


class TempVoice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        if member.guild.id != GUILD_ID or member.bot or before.channel == after.channel:
            return
        config = settings("tempvoice_config")
        if config and config["enabled"] and after.channel and str(after.channel.id) == config["hub_channel_id"]:
            try:
                category = member.guild.get_channel(int(config["category_id"])) if config["category_id"] else after.channel.category
                if category is not None and not isinstance(category, discord.CategoryChannel):
                    raise ValueError("Temporary voice category unavailable")
                name = config["name_template"].replace("{user}", member.display_name)[:100]
                overwrites = {member.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                              member: discord.PermissionOverwrite(view_channel=True, connect=True,
                                                                  manage_channels=True)}
                if member.guild.me:
                    overwrites[member.guild.me] = discord.PermissionOverwrite(view_channel=True,
                                                                               connect=True, move_members=True)
                channel = await member.guild.create_voice_channel(name, category=category,
                    user_limit=config["user_limit"], overwrites=overwrites, reason="Temporary voice channel")
                try:
                    await member.move_to(channel)
                except discord.HTTPException:
                    try:
                        await channel.delete(reason="Owner could not be moved")
                    except discord.HTTPException:
                        log.exception("Could not remove unused temporary voice channel %s", channel.id)
                    raise
                with connect() as db:
                    db.execute("INSERT INTO tempvoice_active (guild_id, channel_id, owner_id, created_at) VALUES (?, ?, ?, ?)",
                               (str(GUILD_ID), str(channel.id), str(member.id), datetime.now(timezone.utc).isoformat()))
            except (discord.Forbidden, discord.HTTPException, ValueError):
                log.exception("Could not create temporary voice channel for %s", member.id)
        if before.channel:
            active = one("SELECT id FROM tempvoice_active WHERE guild_id = ? AND channel_id = ?",
                         (str(GUILD_ID), str(before.channel.id)))
            if active and not before.channel.members:
                try:
                    await before.channel.delete(reason="Empty temporary voice channel")
                    with connect() as db:
                        db.execute("DELETE FROM tempvoice_active WHERE id = ?", (active["id"],))
                except (discord.Forbidden, discord.HTTPException):
                    log.exception("Could not remove temporary voice channel %s", before.channel.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TempVoice(bot))
