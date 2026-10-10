import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID
from db import all_rows, connect, one


log = logging.getLogger(__name__)
BERLIN = ZoneInfo("Europe/Berlin")
EVENT_TYPES = ("Message only", "Discord event only", "Both")


def parse_start(date: str, time: str) -> datetime | None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or not re.fullmatch(r"\d{2}:\d{2}", time):
        return None
    try:
        local = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    utc = local.replace(tzinfo=BERLIN).astimezone(timezone.utc)
    return utc if utc.astimezone(BERLIN).replace(tzinfo=None) == local else None


def announcement(title: str, description: str, start: datetime,
                 event_url: str | None = None) -> discord.Embed:
    stamp = int(start.timestamp())
    embed = discord.Embed(title=title, description=description, timestamp=start,
                          color=discord.Color.blurple())
    embed.add_field(name="Timestamp", value=f"<t:{stamp}:F> · <t:{stamp}:R>", inline=False)
    if event_url:
        embed.add_field(name="Discord event", value=f"[Open event]({event_url})", inline=False)
    return embed


class Events(commands.Cog):
    event = app_commands.guilds(discord.Object(id=GUILD_ID))(
        app_commands.Group(name="event", description="Create and manage community events")
    )

    @event.command(name="create", description="Create a community event")
    @app_commands.describe(
        title="Event title", date="Date (YYYY-MM-DD)",
        time="Time in Europe/Berlin (HH:MM)", description="Optional description",
        type="How the event should be announced",
        channel="Channel to post the announcement (required for Message only and Both)",
        duration_minutes="Duration in minutes for the Discord event (only used for Discord event only and Both)")
    @app_commands.choices(type=[app_commands.Choice(name=value, value=value) for value in EVENT_TYPES])
    async def create(self, interaction: discord.Interaction, title: str, date: str, time: str,
                     description: str = "", type: str = "Message only",
                     channel: discord.TextChannel | None = None,
                     duration_minutes: app_commands.Range[int, 1, 10080] = 60) -> None:
        guild = interaction.guild
        title = title.strip()
        description = description.strip()
        start = parse_start(date, time)
        if guild is None:
            await interaction.response.send_message("Use this command in the server.", ephemeral=True)
            return
        if not 1 <= len(title) <= 100:
            await interaction.response.send_message("The title must contain 1 to 100 characters.", ephemeral=True)
            return
        if len(description) > 1000:
            await interaction.response.send_message("The description must be at most 1000 characters.", ephemeral=True)
            return
        if start is None:
            await interaction.response.send_message(
                "Enter a valid Berlin date and time as YYYY-MM-DD and HH:MM.", ephemeral=True)
            return
        if start <= datetime.now(timezone.utc):
            await interaction.response.send_message("The event must start in the future.", ephemeral=True)
            return
        if type not in EVENT_TYPES:
            await interaction.response.send_message("Choose a valid event type.", ephemeral=True)
            return
        if type in ("Message only", "Both") and channel is None:
            await interaction.response.send_message("Choose a channel for the announcement.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        scheduled: discord.ScheduledEvent | None = None
        message: discord.Message | None = None
        try:
            if type in ("Discord event only", "Both"):
                scheduled = await guild.create_scheduled_event(
                    name=title, description=description, start_time=start,
                    end_time=start + timedelta(minutes=duration_minutes),
                    entity_type=discord.EntityType.external, location="See announcement")
            if type in ("Message only", "Both") and channel is not None:
                message = await channel.send(embed=announcement(
                    title, description, start, scheduled.url if scheduled else None))
            with connect() as db:
                cursor = db.execute(
                    "INSERT INTO scheduled_events (guild_id, title, description, start_at, duration_minutes, "
                    "channel_id, message_id, discord_event_id, created_by, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(GUILD_ID), title, description, start.isoformat(), duration_minutes,
                     str(channel.id) if message and channel else None,
                     str(message.id) if message else None,
                     str(scheduled.id) if scheduled else None, str(interaction.user.id),
                     datetime.now(timezone.utc).isoformat()))
                record_id = cursor.lastrowid
        except Exception:
            if message is not None:
                try:
                    await message.delete()
                except discord.HTTPException:
                    log.exception("Could not remove announcement after event creation failed")
            if scheduled is not None:
                try:
                    await scheduled.delete()
                except discord.HTTPException:
                    log.exception("Could not remove Discord event after creation failed")
            raise
        result = f"Event #{record_id} created."
        if scheduled:
            result += f" {scheduled.url}"
        await interaction.followup.send(result, ephemeral=True)

    @event.command(name="list", description="List upcoming community events")
    async def list_events(self, interaction: discord.Interaction) -> None:
        rows = all_rows("SELECT * FROM scheduled_events WHERE guild_id = ? AND start_at > ? "
                        "ORDER BY start_at, id",
                        (str(GUILD_ID), datetime.now(timezone.utc).isoformat()))
        if not rows:
            await interaction.response.send_message("There are no upcoming events.", ephemeral=True)
            return
        embeds: list[discord.Embed] = []
        for offset in range(0, len(rows), 25):
            embed = discord.Embed(title="Upcoming Events", color=discord.Color.blurple())
            for row in rows[offset:offset + 25]:
                stamp = int(datetime.fromisoformat(row["start_at"]).timestamp())
                embed.add_field(name=f"#{row['id']} · {row['title']}",
                                value=f"<t:{stamp}:R> · Created by <@{row['created_by']}>", inline=False)
            embeds.append(embed)
        await interaction.response.send_message(embeds=embeds[:10], ephemeral=True)
        for offset in range(10, len(embeds), 10):
            await interaction.followup.send(embeds=embeds[offset:offset + 10], ephemeral=True)

    @event.command(name="cancel", description="Cancel a community event by ID")
    @app_commands.describe(id="Event ID shown by /event list")
    async def cancel(self, interaction: discord.Interaction, id: app_commands.Range[int, 1]) -> None:
        row = one("SELECT * FROM scheduled_events WHERE guild_id = ? AND id = ?", (str(GUILD_ID), id))
        if row is None:
            await interaction.response.send_message("Event not found.", ephemeral=True)
            return
        is_admin = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator
        if row["created_by"] != str(interaction.user.id) and not is_admin:
            await interaction.response.send_message("Only the creator or an admin can cancel this event.", ephemeral=True)
            return
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Use this command in the server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        if row["discord_event_id"]:
            try:
                scheduled = await guild.fetch_scheduled_event(int(row["discord_event_id"]))
                await scheduled.delete()
            except discord.NotFound:
                pass
        if row["message_id"] and row["channel_id"]:
            channel = guild.get_channel(int(row["channel_id"]))
            if isinstance(channel, discord.TextChannel):
                try:
                    message = await channel.fetch_message(int(row["message_id"]))
                    await message.edit(embed=discord.Embed(title=row["title"], description="Cancelled"))
                except discord.HTTPException:
                    log.exception("Could not mark event announcement %s cancelled", row["message_id"])
        with connect() as db:
            db.execute("DELETE FROM scheduled_events WHERE guild_id = ? AND id = ?", (str(GUILD_ID), id))
        await interaction.followup.send(f"Event #{id} cancelled.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))
