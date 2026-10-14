import discord
from discord.ext import commands

from config import GUILD_ID
from db import decoded, settings
from utils.embeds import render
from utils.safe import safe_send


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID:
            return
        config = settings("welcome_config")
        if not config:
            return
        roles = [role for role_id in decoded(config["autorole_ids_json"], [])
                 if (role := member.guild.get_role(int(role_id))) is not None]
        if roles:
            await member.add_roles(*roles, reason="Auto roles")
        channel = member.guild.get_channel(int(config["welcome_channel_id"])) if config["welcome_channel_id"] else None
        if isinstance(channel, discord.TextChannel):
            embed = render(decoded(config["welcome_embed_json"], {}), member.guild, member)
            await safe_send(channel,
                content=member.mention,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=False, users=[member], roles=False),
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID:
            return
        config = settings("welcome_config")
        if not config or not config["goodbye_channel_id"]:
            return
        channel = member.guild.get_channel(int(config["goodbye_channel_id"]))
        if isinstance(channel, discord.TextChannel):
            embed = render(decoded(config["goodbye_embed_json"], {}), member.guild, member)
            await safe_send(channel,
                content=member.mention,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=False, users=[member], roles=False),
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
