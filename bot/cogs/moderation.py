"""Guild moderation commands backed by the dashboard configuration."""

import asyncio
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
        self._recent_actions: dict[tuple[int, str, int], datetime] = {}

    def remember_action(self, guild: discord.Guild, action: str, user: discord.abc.User) -> None:
        now = datetime.now(timezone.utc)
        self._recent_actions = {key: seen for key, seen in self._recent_actions.items()
                                if now - seen < timedelta(seconds=30)}
        self._recent_actions[(guild.id, action, user.id)] = now

    def already_logged(self, guild: discord.Guild, action: str, user: discord.abc.User) -> bool:
        seen = self._recent_actions.get((guild.id, action, user.id))
        return seen is not None and datetime.now(timezone.utc) - seen < timedelta(seconds=30)

    async def audit_action(self, guild: discord.Guild, action: discord.AuditLogAction,
                           user: discord.abc.User) -> tuple[discord.AuditLogEntry | None, bool]:
        """Return a recent matching entry and whether the audit log was readable."""
        await asyncio.sleep(1)
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                target = entry.target
                if target is None or target.id != user.id:
                    continue
                if abs((datetime.now(timezone.utc) - entry.created_at).total_seconds()) <= 10:
                    return entry, True
        except (discord.Forbidden, discord.HTTPException):
            log.warning("Could not read moderation audit log in guild %s", guild.id, exc_info=True)
            return None, False
        return None, True

    async def log_native_action(self, guild: discord.Guild, user: discord.abc.User,
                                action: str, title: str, audit_action: discord.AuditLogAction,
                                require_audit_match: bool = False) -> None:
        if guild.id != GUILD_ID or self.already_logged(guild, action, user):
            return
        config = settings("moderation_config") or {}
        if not config.get("log_mod_actions", True) or not config.get("log_channel_id"):
            return
        entry, readable = await self.audit_action(guild, audit_action, user)
        if self.already_logged(guild, action, user):
            return
        if require_audit_match and readable and entry is None:
            return
        if entry and self.bot.user and entry.user and entry.user.id == self.bot.user.id:
            return
        moderator = entry.user if entry else None
        reason = entry.reason if entry and entry.reason else "No reason provided"
        await self.report(guild, title, user, moderator, reason)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        await self.log_native_action(guild, user, "ban", "Member banned",
                                     discord.AuditLogAction.ban)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        await self.log_native_action(guild, user, "unban", "Member unbanned",
                                     discord.AuditLogAction.unban)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await self.log_native_action(member.guild, member, "kick", "Member kicked",
                                     discord.AuditLogAction.kick, require_audit_match=True)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        old = before.communication_disabled_until
        new = after.communication_disabled_until
        if old == new:
            return
        now = datetime.now(timezone.utc)
        if new is not None and new > now:
            action, title = "timeout", "Member timed out"
        elif old is not None and old > now:
            action, title = "untimeout", "Timeout removed"
        else:
            return
        await self.log_native_action(after.guild, after, action, title,
                                     discord.AuditLogAction.member_update,
                                     require_audit_match=action == "untimeout")

    async def report(self, guild: discord.Guild, title: str, member: discord.abc.User,
                     moderator: discord.abc.User | None, reason: str) -> None:
        config = settings("moderation_config")
        channel = guild.get_channel(int(config["log_channel_id"])) if config and config["log_channel_id"] else None
        if isinstance(channel, discord.TextChannel):
            color = (0x57F287 if title == "Member unbanned" else
                     0xFAA61A if title in {"Member timed out", "Timeout removed"} else 0xED4245)
            now = datetime.now(timezone.utc)
            embed = discord.Embed(title=title, color=color, timestamp=now)
            embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)")
            embed.add_field(name="Moderator", value=(f"{moderator.mention} (`{moderator.id}`)"
                                                       if moderator else "Unknown"))
            embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
            embed.add_field(name="Timestamp", value=f"<t:{int(now.timestamp())}:F>", inline=False)
            embed.set_footer(text=self.bot.user.display_name if self.bot.user else "Bot")
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
                self.remember_action(interaction.guild, "ban", user)
                await interaction.guild.ban(user, reason=f"Warning threshold: {reason}")
                action = " Banned at the configured threshold."
                await self.report(interaction.guild, "Member banned", user, interaction.user,
                                  f"Warning threshold reached: {reason}")
            elif count >= config.get("warn_kick_threshold", 3):
                self.remember_action(interaction.guild, "kick", user)
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
        self.remember_action(interaction.guild, "timeout", user)
        await user.timeout(timedelta(seconds=duration.value), reason=reason)
        await self.report(interaction.guild, "Member muted", user, interaction.user, reason)
        await interaction.response.send_message(f"Timed out {user.mention} for {duration.name}.", ephemeral=True)

    @app_commands.command(name="unmute", description="Remove a member's timeout")
    @app_commands.describe(user="Member whose timeout to remove")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.guilds(GUILD)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member) -> None:
        self.remember_action(interaction.guild, "untimeout", user)
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
        self.remember_action(interaction.guild, "ban", user)
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
        self.remember_action(interaction.guild, "kick", user)
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
