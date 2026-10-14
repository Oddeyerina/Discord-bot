import asyncio
import logging
import re
import unicodedata
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID
from db import connect, one, settings

log = logging.getLogger(__name__)


def emoji_prefix(channel_name: str) -> str:
    prefix = channel_name.split(" ", 1)[0]
    if re.fullmatch(r"<a?:[A-Za-z0-9_]+:\d+>", prefix):
        return prefix
    if any(unicodedata.category(character) == "So" for character in prefix) and all(
        unicodedata.category(character) in {"So", "Sk", "Mn", "Me"} or character == "\u200d"
        for character in prefix
    ):
        return prefix
    return ""


class TempVoice(commands.Cog):
    tempvoice = app_commands.guilds(discord.Object(id=GUILD_ID))(
        app_commands.Group(name="tempvoice", description="Manage your temporary voice channel")
    )

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._channel_locks: dict[int, asyncio.Lock] = {}

    async def current_channel(self, interaction: discord.Interaction,
                              owner_only: bool = True) -> tuple[discord.VoiceChannel, dict] | None:
        guild = interaction.guild
        config = settings("tempvoice_config")
        if (interaction.guild_id != GUILD_ID or not config or not config["control_channel_id"] or
                str(interaction.channel_id) != config["control_channel_id"]):
            await interaction.response.send_message(
                "Please use this command in the configured control channel.", ephemeral=True)
            return None
        voice = getattr(interaction.user, "voice", None)
        channel = voice.channel if voice else None
        if not isinstance(channel, discord.VoiceChannel) or guild is None or channel.guild.id != guild.id:
            await interaction.response.send_message(
                "Join a temporary voice channel before using its commands.", ephemeral=True)
            return None
        active = one("SELECT * FROM tempvoice_active WHERE guild_id = ? AND channel_id = ?",
                     (str(GUILD_ID), str(channel.id)))
        if active is None:
            await interaction.response.send_message("This is not a temporary voice channel.", ephemeral=True)
            return None
        if owner_only and str(interaction.user.id) != active["owner_id"]:
            await interaction.response.send_message("Only the channel owner can do that.", ephemeral=True)
            return None
        return channel, active

    @tempvoice.command(name="name", description="Rename your temporary voice channel")
    @app_commands.describe(name="New channel name")
    async def rename(self, interaction: discord.Interaction, name: str) -> None:
        context = await self.current_channel(interaction)
        if context is None:
            return
        name = name.strip()
        if not 1 <= len(name) <= 100:
            await interaction.response.send_message("The name must contain 1 to 100 characters.", ephemeral=True)
            return
        channel, _ = context
        prefix = emoji_prefix(channel.name)
        if prefix:
            name = name.removeprefix(f"{prefix} ").strip()
            name = f"{prefix} {name}"[:100]
        try:
            await channel.edit(name=name, reason=f"Temporary voice owner {interaction.user.id} renamed channel")
        except discord.HTTPException:
            log.exception("Could not rename temporary voice channel %s", channel.id)
            await interaction.response.send_message("Could not rename this channel.", ephemeral=True)
            return
        await interaction.response.send_message(f"Channel renamed to {name}.", ephemeral=True)

    @tempvoice.command(name="limit", description="Set the maximum number of users, or zero for unlimited")
    @app_commands.describe(limit="User limit (0 = unlimited)")
    async def limit(self, interaction: discord.Interaction, limit: app_commands.Range[int, 0, 99]) -> None:
        context = await self.current_channel(interaction)
        if context is None:
            return
        if not 0 <= limit <= 99:
            await interaction.response.send_message("The user limit must be between 0 and 99.", ephemeral=True)
            return
        channel, _ = context
        try:
            await channel.edit(user_limit=limit, reason=f"Temporary voice owner {interaction.user.id} changed limit")
        except discord.HTTPException:
            log.exception("Could not change temporary voice limit for %s", channel.id)
            await interaction.response.send_message("Could not change the user limit.", ephemeral=True)
            return
        await interaction.response.send_message(
            "User limit removed." if limit == 0 else f"User limit set to {limit}.", ephemeral=True)

    @tempvoice.command(name="lock", description="Lock the channel (deny connect for @everyone)")
    async def lock(self, interaction: discord.Interaction) -> None:
        await self.set_public_access(interaction, allow=False)

    @tempvoice.command(name="unlock", description="Unlock the channel (allow connect for @everyone)")
    async def unlock(self, interaction: discord.Interaction) -> None:
        await self.set_public_access(interaction, allow=True)

    async def set_public_access(self, interaction: discord.Interaction, allow: bool) -> None:
        context = await self.current_channel(interaction)
        if context is None:
            return
        channel, _ = context
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.connect = allow
        if allow:
            overwrite.view_channel = True
        try:
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite,
                                          reason=f"Temporary voice owner {interaction.user.id} changed access")
        except discord.HTTPException:
            log.exception("Could not change access for temporary voice channel %s", channel.id)
            await interaction.response.send_message("Could not change channel access.", ephemeral=True)
            return
        await interaction.response.send_message("Channel unlocked." if allow else "Channel locked.", ephemeral=True)

    @tempvoice.command(name="claim", description="Take ownership if the current owner left")
    async def claim(self, interaction: discord.Interaction) -> None:
        context = await self.current_channel(interaction, owner_only=False)
        if context is None:
            return
        channel, _ = context
        async with self._channel_locks.setdefault(channel.id, asyncio.Lock()):
            active = one("SELECT * FROM tempvoice_active WHERE guild_id = ? AND channel_id = ?",
                         (str(GUILD_ID), str(channel.id)))
            if active is None:
                await interaction.response.send_message("This channel is no longer temporary.", ephemeral=True)
                return
            if active["owner_id"] == str(interaction.user.id):
                await interaction.response.send_message("You already own this channel.", ephemeral=True)
                return
            if any(str(member.id) == active["owner_id"] for member in channel.members):
                await interaction.response.send_message("The current owner is still in this channel.", ephemeral=True)
                return
            overwrites = channel.overwrites.copy()
            for target in list(overwrites):
                if not isinstance(target, discord.Role) and str(target.id) == active["owner_id"]:
                    del overwrites[target]
            overwrites[interaction.user] = discord.PermissionOverwrite(view_channel=True,
                                                                        connect=True, manage_channels=True)
            try:
                await channel.edit(overwrites=overwrites, reason=f"Temporary voice ownership claimed by {interaction.user.id}")
            except discord.HTTPException:
                log.exception("Could not transfer temporary voice channel %s", channel.id)
                await interaction.response.send_message("Could not claim this channel.", ephemeral=True)
                return
            with connect() as db:
                db.execute("UPDATE tempvoice_active SET owner_id = ? WHERE id = ? AND owner_id = ?",
                           (str(interaction.user.id), active["id"], active["owner_id"]))
        await interaction.response.send_message("You now own this channel.", ephemeral=True)

    @tempvoice.command(name="delete", description="Delete this temporary channel")
    async def delete(self, interaction: discord.Interaction) -> None:
        context = await self.current_channel(interaction)
        if context is None:
            return
        channel, active = context
        await interaction.response.defer(ephemeral=True)
        async with self._channel_locks.setdefault(channel.id, asyncio.Lock()):
            try:
                await channel.delete(reason=f"Temporary voice owner {interaction.user.id} deleted channel")
            except discord.NotFound:
                pass
            except discord.HTTPException:
                log.exception("Could not delete temporary voice channel %s", channel.id)
                await interaction.followup.send("Could not delete this channel.", ephemeral=True)
                return
            with connect() as db:
                db.execute("DELETE FROM tempvoice_active WHERE id = ?", (active["id"],))
        await interaction.followup.send("Temporary voice channel deleted.", ephemeral=True)

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
            async with self._channel_locks.setdefault(before.channel.id, asyncio.Lock()):
                active = one("SELECT id FROM tempvoice_active WHERE guild_id = ? AND channel_id = ?",
                             (str(GUILD_ID), str(before.channel.id)))
                if active and not before.channel.members:
                    try:
                        await before.channel.delete(reason="Empty temporary voice channel")
                    except discord.NotFound:
                        pass
                    except discord.HTTPException:
                        log.exception("Could not remove temporary voice channel %s", before.channel.id)
                        return
                    with connect() as db:
                        db.execute("DELETE FROM tempvoice_active WHERE id = ?", (active["id"],))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TempVoice(bot))
