import logging
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from config import GUILD_ID
from db import decoded, settings

log = logging.getLogger(__name__)


class Honeypot(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def trigger(self, member: discord.Member, channel: discord.abc.GuildChannel,
                      message: discord.Message | None = None) -> None:
        config = settings("honeypot_config")
        if not config or str(channel.id) != config["channel_id"] or member.bot:
            return
        if member.guild_permissions.administrator or any(
            str(role.id) in decoded(config["whitelist_role_ids_json"], []) for role in member.roles
        ):
            return
        if message and config["delete_message"]:
            try:
                await message.delete()
            except discord.Forbidden:
                pass
        if config["dm_user"]:
            try:
                await member.send("You triggered a protected channel rule.")
            except discord.Forbidden:
                pass
        action = config["action"]
        try:
            if action == "ban":
                await member.ban(reason="Honeypot channel triggered")
            elif action == "timeout":
                await member.timeout(datetime.now(timezone.utc) + timedelta(seconds=config["timeout_seconds"]),
                                     reason="Honeypot channel triggered")
            else:
                await member.kick(reason="Honeypot channel triggered")
        except discord.HTTPException as exc:
            log.warning("Honeypot %s failed for member %s: %s", action, member.id, exc, exc_info=True)
            return
        log_channel = member.guild.get_channel(int(config["log_channel_id"])) if config["log_channel_id"] else None
        if isinstance(log_channel, discord.TextChannel):
            embed = discord.Embed(title="Honeypot triggered", color=0xED4245,
                                  timestamp=datetime.now(timezone.utc))
            embed.description = f"User: {member.mention}\nAction: {action}\nChannel: {channel.mention}"
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild and message.guild.id == GUILD_ID and isinstance(message.author, discord.Member):
            await self.trigger(message.author, message.channel, message)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id != GUILD_ID:
            return
        guild = self.bot.get_guild(GUILD_ID)
        member = payload.member or (guild.get_member(payload.user_id) if guild else None)
        channel = guild.get_channel(payload.channel_id) if guild else None
        if member and channel:
            await self.trigger(member, channel)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Honeypot(bot))
