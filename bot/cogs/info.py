from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID


def relative_time(value: datetime | None) -> str:
    return f"<t:{int(value.timestamp())}:R>" if value else "Unknown"


class Info(commands.Cog):
    @app_commands.command(name="userinfo", description="Show information about a server member")
    @app_commands.describe(user="Member to check (default: yourself)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        member = target if isinstance(target, discord.Member) else None
        top_role = member.top_role if member else None
        role_name = top_role.mention if top_role and not top_role.is_default() else "None"
        embed = discord.Embed(title=f"{target.display_name} ({target})", color=discord.Color.blurple())
        embed.add_field(name="User ID", value=str(target.id))
        embed.add_field(name="Account created", value=relative_time(target.created_at))
        embed.add_field(name="Joined server", value=relative_time(member.joined_at) if member else "Unknown")
        embed.add_field(name="Top role", value=role_name)
        embed.add_field(name="Roles", value=str(max(len(member.roles) - 1, 0)) if member else "0")
        embed.add_field(name="Account type", value="Bot" if target.bot else "User")
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="serverinfo", description="Show information about this server")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Use this command in the server.", ephemeral=True)
            return
        bots = sum(member.bot for member in guild.members)
        humans = len(guild.members) - bots
        total = guild.member_count or len(guild.members)
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Server ID", value=str(guild.id))
        embed.add_field(name="Owner", value=f"<@{guild.owner_id}>")
        embed.add_field(name="Created", value=relative_time(guild.created_at))
        embed.add_field(name="Members", value=f"{total} total · {humans} humans · {bots} bots", inline=False)
        embed.add_field(name="Boosts", value=f"Level {guild.premium_tier} · {guild.premium_subscription_count or 0} boosts")
        embed.add_field(name="Channels", value=(f"{len(guild.text_channels)} text · "
                                                 f"{len(guild.voice_channels)} voice · "
                                                 f"{len(guild.categories)} categories"), inline=False)
        embed.add_field(name="Roles", value=str(len(guild.roles)))
        embed.add_field(name="Emojis", value=str(len(guild.emojis)))
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Info())
