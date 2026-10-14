"""Guild moderation commands backed by the dashboard configuration."""

from datetime import datetime, timedelta, timezone
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID
from db import all_rows, connect, settings
from utils.safe import safe_send

log = logging.getLogger(__name__)
GUILD = discord.Object(id=GUILD_ID)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def report(self, guild: discord.Guild, title: str, member: discord.abc.User,
                     moderator: discord.abc.User, reason: str) -> None:
        config = settings("moderation_config")
        channel = guild.get_channel(int(config["log_channel_id"])) if config and config["log_channel_id"] else None
        if isinstance(channel, discord.TextChannel):
            embed = discord.Embed(title=title, color=0xED4245,
                                  timestamp=datetime.now(timezone.utc))
            embed.add_field(name="Member", value=f"{member.mention} (`{member.id}`)")
            embed.add_field(name="Moderator", value=moderator.mention)
            embed.add_field(name="Reason", value=reason, inline=False)
            await safe_send(channel, embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="warn", description="Warn a member and apply configured thresholds")
    @app_commands.describe(user="Member to warn", reason="Reason for the warning")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.guilds(GUILD)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str) -> None:
        if user.bot or user == interaction.user:
            await interaction.response.send_message("Choose another human member.", ephemeral=True)
            return
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("You cannot warn a member with an equal or higher role.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        config = settings("moderation_config") or {}
        with connect() as db:
            db.execute("INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at) "
                       "VALUES (?, ?, ?, ?, ?)",
                       (str(GUILD_ID), str(user.id), str(interaction.user.id), reason,
                        datetime.now(timezone.utc).isoformat()))
            count = db.execute("SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?",
                               (str(GUILD_ID), str(user.id))).fetchone()[0]
        if config.get("dm_on_warn", True):
            await safe_send(user, content=f"You received a warning in {interaction.guild.name}: {reason}")
        action = ""
        try:
            if count >= config.get("warn_ban_threshold", 5):
                await interaction.guild.ban(user, reason=f"Warning threshold: {reason}")
                action = " Banned at the configured threshold."
                await self.report(interaction.guild, "Member banned", user, interaction.user,
                                  f"Warning threshold reached: {reason}")
            elif count >= config.get("warn_kick_threshold", 3):
                await user.kick(reason=f"Warning threshold: {reason}")
                action = " Kicked at the configured threshold."
                await self.report(interaction.guild, "Member kicked", user, interaction.user,
                                  f"Warning threshold reached: {reason}")
        except discord.HTTPException:
            log.exception("Could not enforce warning threshold for %s", user.id)
            action = " Threshold action failed; check bot permissions."
        await self.report(interaction.guild, "Member warned", user, interaction.user, reason)
        await interaction.followup.send(f"Warned {user.mention} ({count} total).{action}", ephemeral=True)

    @app_commands.command(name="warns", description="Show a member's warnings")
    @app_commands.describe(user="Member whose warnings to show")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.guilds(GUILD)
    async def warns(self, interaction: discord.Interaction, user: discord.Member) -> None:
        rows = all_rows("SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
                        (str(GUILD_ID), str(user.id)))
        if not rows:
            await interaction.response.send_message("No warnings for this member.", ephemeral=True)
            return
        chunks: list[str] = []
        current = ""
        for row in rows:
            line = f"#{row['id']} — {row['reason'][:300]} (by <@{row['moderator_id']}>)\n"
            if len(current) + len(line) > 1900:
                chunks.append(current)
                current = ""
            current += line
        if current:
            chunks.append(current)
        await interaction.response.send_message(chunks[0], ephemeral=True)
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk, ephemeral=True)

    @app_commands.command(name="clearwarns", description="Clear a member's warnings")
    @app_commands.describe(user="Member whose warnings to clear")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def clearwarns(self, interaction: discord.Interaction, user: discord.Member) -> None:
        with connect() as db:
            count = db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
                               (str(GUILD_ID), str(user.id))).rowcount
        await self.report(interaction.guild, "Warnings cleared", user, interaction.user, f"{count} removed")
        await interaction.response.send_message(f"Cleared {count} warning(s) for {user.mention}.", ephemeral=True)

    @app_commands.command(name="mute", description="Time out a member")
    @app_commands.describe(user="Member to time out", duration="Timeout duration", reason="Reason for the timeout")
    @app_commands.choices(duration=[app_commands.Choice(name=name, value=seconds) for name, seconds in
                                     (("60 seconds", 60), ("5 minutes", 300), ("10 minutes", 600),
                                      ("1 hour", 3600), ("1 day", 86400), ("7 days", 604800))])
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.guilds(GUILD)
    async def mute(self, interaction: discord.Interaction, user: discord.Member,
                   duration: app_commands.Choice[int], reason: str) -> None:
        await user.timeout(timedelta(seconds=duration.value), reason=reason)
        await self.report(interaction.guild, "Member muted", user, interaction.user, reason)
        await interaction.response.send_message(f"Timed out {user.mention} for {duration.name}.", ephemeral=True)

    @app_commands.command(name="unmute", description="Remove a member's timeout")
    @app_commands.describe(user="Member whose timeout to remove")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.guilds(GUILD)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await user.timeout(None, reason="Timeout removed")
        await self.report(interaction.guild, "Member unmuted", user, interaction.user, "Timeout removed")
        await interaction.response.send_message(f"Removed timeout for {user.mention}.", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.describe(user="Member to ban", reason="Reason for the ban", delete_messages_days="Days of messages to delete (0-7)")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.guilds(GUILD)
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str,
                  delete_messages_days: app_commands.Range[int, 0, 7] = 0) -> None:
        await interaction.guild.ban(user, reason=reason,
                                    delete_message_seconds=delete_messages_days * 86400)
        await self.report(interaction.guild, "Member banned", user, interaction.user, reason)
        await interaction.response.send_message(f"Banned {user.mention}.", ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.describe(user="Member to kick", reason="Reason for the kick")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.guilds(GUILD)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str) -> None:
        await user.kick(reason=reason)
        await self.report(interaction.guild, "Member kicked", user, interaction.user, reason)
        await interaction.response.send_message(f"Kicked {user.mention}.", ephemeral=True)

    @app_commands.command(name="slowmode", description="Set this channel's slowmode")
    @app_commands.describe(seconds="Delay between messages in seconds (0 disables slowmode)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.guilds(GUILD)
    async def slowmode(self, interaction: discord.Interaction,
                       seconds: app_commands.Range[int, 0, 21600]) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use this in a text channel.", ephemeral=True)
            return
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(f"Slowmode set to {seconds} seconds.", ephemeral=True)

    @app_commands.command(name="lock", description="Deny sending messages in a channel")
    @app_commands.describe(channel="Channel to lock (default: current channel)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.guilds(GUILD)
    async def lock(self, interaction: discord.Interaction,
                   channel: discord.TextChannel | None = None) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Use this in a text channel.", ephemeral=True)
            return
        await target.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("Channel locked.", ephemeral=True)

    @app_commands.command(name="unlock", description="Allow sending messages in a channel")
    @app_commands.describe(channel="Channel to unlock (default: current channel)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.guilds(GUILD)
    async def unlock(self, interaction: discord.Interaction,
                     channel: discord.TextChannel | None = None) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Use this in a text channel.", ephemeral=True)
            return
        await target.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message("Channel unlocked.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
