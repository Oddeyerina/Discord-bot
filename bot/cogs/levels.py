import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import GUILD_ID
from db import all_rows, connect, decoded, one, settings
from utils.embeds import render
from utils.safe import safe_send

log = logging.getLogger(__name__)


def level_from_xp(xp: int, base: int, multiplier: float) -> int:
    level = 0
    remaining = xp
    while level < 1000:
        cost = round(base * multiplier ** level)
        if remaining < cost:
            break
        remaining -= cost
        level += 1
    return level


class Levels(commands.Cog):
    leaderboard = app_commands.Group(name="leaderboard", description="Show member leaderboards",
                                     guild_ids=[GUILD_ID])

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._voice_tasks: dict[int, asyncio.Task[None]] = {}

    def cog_unload(self) -> None:
        self.refresh_voice_tracking.cancel()
        for task in self._voice_tasks.values():
            task.cancel()
        self._voice_tasks.clear()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self.refresh_voice_tracking.is_running():
            self.refresh_voice_tracking.start()
        guild = self.bot.get_guild(GUILD_ID)
        if guild:
            for task in self._voice_tasks.values():
                task.cancel()
            self._voice_tasks.clear()
            for channel in guild.voice_channels:
                for member in channel.members:
                    self._reconcile_voice(member, channel, guild)

    @tasks.loop(minutes=1)
    async def refresh_voice_tracking(self) -> None:
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return
        present: set[int] = set()
        for channel in guild.voice_channels:
            for member in channel.members:
                present.add(member.id)
                self._reconcile_voice(member, channel, guild)
        for member_id in set(self._voice_tasks) - present:
            self._cancel_voice(member_id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState) -> None:
        if member.guild.id != GUILD_ID:
            return
        if before.channel != after.channel:
            self._cancel_voice(member.id)
        for channel in (before.channel, after.channel):
            if channel is None:
                continue
            for occupant in channel.members:
                self._reconcile_voice(occupant, channel, member.guild)
        if after.channel is None:
            self._cancel_voice(member.id)

    def _cancel_voice(self, member_id: int) -> None:
        task = self._voice_tasks.pop(member_id, None)
        if task is not None:
            task.cancel()

    def _reconcile_voice(self, member: discord.Member, channel: discord.abc.GuildChannel,
                         guild: discord.Guild) -> None:
        if self._eligible_voice(member, channel, guild):
            if member.id not in self._voice_tasks:
                self._voice_tasks[member.id] = asyncio.create_task(self._voice_worker(member))
        else:
            self._cancel_voice(member.id)

    def _eligible_voice(self, member: discord.Member, channel: discord.abc.GuildChannel,
                        guild: discord.Guild) -> bool:
        config = settings("level_config")
        return bool(config and config["voice_xp_per_minute"] > 0 and not member.bot and
                    channel != guild.afk_channel and
                    str(channel.id) not in decoded(config["voice_ignored_channel_ids_json"], []) and
                    len([other for other in channel.members if not other.bot]) > 1)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild or message.guild.id != GUILD_ID or message.author.bot:
            return
        config = settings("level_config")
        if not config or str(message.channel.id) in decoded(config["ignored_channel_ids_json"], []):
            return
        if isinstance(message.author, discord.Member) and any(
            str(role.id) in decoded(config["ignored_role_ids_json"], []) for role in message.author.roles
        ):
            return
        now = datetime.now(timezone.utc)
        row = one("SELECT * FROM level_users WHERE guild_id = ? AND user_id = ?",
                  (str(GUILD_ID), str(message.author.id)))
        if row and row["last_xp_at"]:
            previous = datetime.fromisoformat(row["last_xp_at"])
            if previous.tzinfo is None:
                previous = previous.replace(tzinfo=timezone.utc)
            if (now - previous).total_seconds() < config["cooldown_seconds"]:
                return
        previous_level = row["level"] if row else 0
        xp = (row["xp"] if row else 0) + config["xp_per_message"]
        level = level_from_xp(xp, config["base_xp"], config["multiplier"])
        with connect() as db:
            db.execute("INSERT INTO level_users (guild_id, user_id, xp, level, last_xp_at, messages_count) VALUES (?, ?, ?, ?, ?, 1) "
                       "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp=excluded.xp, level=excluded.level, "
                       "last_xp_at=excluded.last_xp_at, messages_count=level_users.messages_count+1",
                       (str(GUILD_ID), str(message.author.id), xp, level, now.isoformat()))
        if level <= previous_level:
            return
        if isinstance(message.author, discord.Member):
            for mapping in all_rows("SELECT * FROM level_roles WHERE guild_id = ? AND level > ? AND level <= ?",
                                    (str(GUILD_ID), previous_level, level)):
                role = message.guild.get_role(int(mapping["role_id"]))
                if role:
                    await message.author.add_roles(role, reason="Level reward")
        channel = message.guild.get_channel(int(config["announcement_channel_id"])) if config["announcement_channel_id"] else None
        if isinstance(channel, discord.TextChannel):
            template = decoded(config["levelup_embed_json"], {})
            if template.get("title") or template.get("description"):
                await safe_send(channel, embed=render(template, message.guild, message.author, level))

    async def _voice_worker(self, member: discord.Member) -> None:
        try:
            while True:
                await asyncio.sleep(60)
                channel = member.voice.channel if member.voice else None
                guild = member.guild
                if channel is None or not self._eligible_voice(member, channel, guild):
                    return
                config = settings("level_config")
                if config is None:
                    return
                now = datetime.now(timezone.utc)
                row = one("SELECT * FROM level_users WHERE guild_id = ? AND user_id = ?",
                          (str(GUILD_ID), str(member.id)))
                old_level = row["level"] if row else 0
                xp = (row["xp"] if row else 0) + config["voice_xp_per_minute"]
                level = level_from_xp(xp, config["base_xp"], config["multiplier"])
                with connect() as db:
                    db.execute("INSERT INTO level_users (guild_id, user_id, xp, level, voice_seconds_last_grant) "
                               "VALUES (?, ?, ?, ?, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET "
                               "xp=excluded.xp, level=excluded.level, voice_seconds_last_grant=excluded.voice_seconds_last_grant",
                               (str(GUILD_ID), str(member.id), xp, level, now.isoformat()))
                if level > old_level:
                    for mapping in all_rows("SELECT * FROM level_roles WHERE guild_id = ? AND level > ? AND level <= ?",
                                            (str(GUILD_ID), old_level, level)):
                        role = guild.get_role(int(mapping["role_id"]))
                        if role:
                            await member.add_roles(role, reason="Level reward")
                    target = guild.get_channel(int(config["announcement_channel_id"])) if config["announcement_channel_id"] else None
                    if isinstance(target, discord.TextChannel):
                        template = decoded(config["levelup_embed_json"], {})
                        if template.get("title") or template.get("description"):
                            await safe_send(target, embed=render(template, guild, member, level))
        except Exception:
            log.exception("Voice XP timer failed for member %s", member.id)
        finally:
            if self._voice_tasks.get(member.id) is asyncio.current_task():
                self._voice_tasks.pop(member.id, None)

    @app_commands.command(name="rank", description="Show your rank or another member's rank")
    @app_commands.describe(user="Member to check (default: yourself)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        row = one("SELECT * FROM level_users WHERE guild_id = ? AND user_id = ?",
                  (str(GUILD_ID), str(target.id)))
        await interaction.response.send_message(
            f"**{target.display_name}** — Level {row['level'] if row else 0} — "
            f"{row['xp'] if row else 0} XP", ephemeral=True)

    @app_commands.command(name="stats", description="Show a member's level and server stats")
    @app_commands.describe(user="Member to check (default: yourself)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def stats(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        row = one("SELECT * FROM level_users WHERE guild_id = ? AND user_id = ?",
                  (str(GUILD_ID), str(target.id)))
        joined = f"<t:{int(target.joined_at.timestamp())}:D>" if isinstance(target, discord.Member) and target.joined_at else "Unknown"
        roles = ", ".join(role.mention for role in target.roles if role != interaction.guild.default_role) if isinstance(target, discord.Member) else "None"
        await interaction.response.send_message(
            f"**{target.display_name}**\nLevel: {row['level'] if row else 0} • XP: {row['xp'] if row else 0}\n"
            f"Messages: {row['messages_count'] if row else 0}\nJoined: {joined}\nRoles: {roles or 'None'}",
            ephemeral=True)

    @leaderboard.command(name="xp", description="Show the top 10 members by XP")
    async def leaderboard_xp(self, interaction: discord.Interaction) -> None:
        await self.show_leaderboard(interaction, "xp", "XP")

    @leaderboard.command(name="messages", description="Show the top 10 members by messages")
    async def leaderboard_messages(self, interaction: discord.Interaction) -> None:
        await self.show_leaderboard(interaction, "messages_count", "messages")

    async def show_leaderboard(self, interaction: discord.Interaction, column: str,
                               label: str) -> None:
        rows = all_rows(f"SELECT * FROM level_users WHERE guild_id = ? ORDER BY {column} DESC LIMIT 10",
                        (str(GUILD_ID),))
        content = "\n".join(f"{i}. <@{r['user_id']}> — {r[column]} {label}"
                            for i, r in enumerate(rows, 1))
        await interaction.response.send_message(
            f"**Top 10 members by {label}**\n{content}" if content else "No ranks yet.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Levels(bot))
