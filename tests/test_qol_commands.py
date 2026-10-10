"""Exercise poll, event, and slash-error paths without Discord network access."""

import asyncio
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import discord
from discord import app_commands


class FakeResponse:
    def __init__(self) -> None:
        self.calls: list[tuple[object, dict]] = []
        self.deferred = False

    async def send_message(self, content: object = None, **kwargs: object) -> None:
        self.calls.append((content, kwargs))

    async def send(self, content: object = None, **kwargs: object) -> None:
        await self.send_message(content, **kwargs)

    async def defer(self, *, ephemeral: bool) -> None:
        assert ephemeral
        self.deferred = True

    def is_done(self) -> bool:
        return self.deferred or bool(self.calls)


class FakeMessage:
    id = 1234

    def __init__(self) -> None:
        self.edited = False
        self.deleted = False

    async def edit(self, **kwargs: object) -> None:
        self.edited = True
        assert kwargs["embed"].description == "Cancelled"

    async def delete(self) -> None:
        self.deleted = True


class FakeChannel:
    id = 5678

    def __init__(self) -> None:
        self.message = FakeMessage()
        self.sent: list[discord.Embed] = []

    async def send(self, *, embed: discord.Embed) -> FakeMessage:
        self.sent.append(embed)
        return self.message

    async def fetch_message(self, message_id: int) -> FakeMessage:
        assert message_id == self.message.id
        return self.message


class FakeScheduled:
    id = 9012
    url = "https://discord.com/events/123456789/9012"

    def __init__(self) -> None:
        self.deleted = False

    async def delete(self) -> None:
        self.deleted = True


async def test_commands(database_path: Path) -> None:
    from cogs import events, poll
    from main import SuiteBot

    channel = FakeChannel()
    scheduled = FakeScheduled()

    async def create_scheduled_event(**kwargs: object) -> FakeScheduled:
        assert kwargs["entity_type"] == discord.EntityType.external
        assert kwargs["location"] == "See announcement"
        return scheduled

    async def fetch_scheduled_event(event_id: int) -> FakeScheduled:
        assert event_id == scheduled.id
        return scheduled

    guild = SimpleNamespace(create_scheduled_event=create_scheduled_event,
                            fetch_scheduled_event=fetch_scheduled_event,
                            get_channel=lambda channel_id: channel if channel_id == channel.id else None)

    def interaction(user_id: int = 42) -> SimpleNamespace:
        return SimpleNamespace(guild=guild, user=SimpleNamespace(id=user_id),
                               response=FakeResponse(), followup=FakeResponse(), command="event")

    berlin = ZoneInfo("Europe/Berlin")
    future = datetime.now(berlin) + timedelta(days=2)
    future = future.replace(hour=20, minute=0)
    assert events.parse_start("2026-02-30", "20:00") is None
    assert events.parse_start("2026-03-29", "02:30") is None
    assert events.parse_start(future.strftime("%Y-%m-%d"), "20:00") is not None

    event_cog = events.Events(None)
    creator = interaction()
    await event_cog.create.callback(event_cog, creator, "Game night", future.strftime("%Y-%m-%d"),
                                    "20:00", "Join us", "Both", channel, 60)
    assert creator.response.deferred
    assert channel.sent[0].title == "Game night"
    assert "discord.com/events" in channel.sent[0].fields[1].value
    assert creator.followup.calls[0][1]["ephemeral"] is True
    with closing(sqlite3.connect(database_path)) as db:
        row = db.execute("SELECT id, created_by, message_id, discord_event_id FROM scheduled_events").fetchone()
    assert row[1:] == ("42", "1234", "9012")

    viewer = interaction()
    await event_cog.list_events.callback(event_cog, viewer)
    assert viewer.response.calls[0][1]["ephemeral"] is True
    assert "Game night" in viewer.response.calls[0][1]["embeds"][0].fields[0].name

    stranger = interaction(43)
    await event_cog.cancel.callback(event_cog, stranger, row[0])
    assert "Only the creator" in stranger.response.calls[0][0]
    original_channel = events.discord.TextChannel
    events.discord.TextChannel = FakeChannel
    try:
        owner = interaction()
        await event_cog.cancel.callback(event_cog, owner, row[0])
    finally:
        events.discord.TextChannel = original_channel
    assert scheduled.deleted and channel.message.edited
    with closing(sqlite3.connect(database_path)) as db:
        assert db.execute("SELECT id FROM scheduled_events").fetchone() is None

    poll_cog = poll.Polls()
    short_poll = interaction()
    await poll_cog.poll.callback(poll_cog, short_poll, "Question?", "Yes", "No", duration=15)
    assert "at least one hour" in short_poll.response.calls[0][0]
    valid_poll = interaction()
    await poll_cog.poll.callback(poll_cog, valid_poll, "Question?", "Yes", "No")
    assert isinstance(valid_poll.response.calls[0][1]["poll"], discord.Poll)
    assert valid_poll.response.calls[0][1].get("ephemeral") is None

    bot = SuiteBot()
    error_interaction = interaction()
    await bot.on_app_command_error(error_interaction, app_commands.MissingPermissions(["manage_guild"]))
    assert "required permissions" in error_interaction.response.calls[0][0]
    error_interaction.response.deferred = True
    await bot.on_app_command_error(error_interaction, app_commands.MissingPermissions(["manage_guild"]))
    assert error_interaction.followup.calls[0][1]["ephemeral"] is True
    cooldown = interaction()
    await bot.on_app_command_error(cooldown, app_commands.CommandOnCooldown(
        app_commands.Cooldown(1, 60), 2.5))
    assert "2.5 seconds" in cooldown.response.calls[0][0]
    unexpected = interaction()
    await bot.on_app_command_error(unexpected, app_commands.AppCommandError("Unexpected"))
    assert unexpected.response.calls[0][0] == "Something went wrong. The error has been logged."
    await bot.close()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "events.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["DISCORD_TOKEN"] = "test-token"
        os.environ["DISCORD_GUILD_ID"] = "123456789"
        os.environ["SESSION_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
        sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))
        with closing(sqlite3.connect(database_path)) as db:
            db.execute("CREATE TABLE scheduled_events (id INTEGER PRIMARY KEY, guild_id TEXT, title TEXT, "
                       "description TEXT, start_at TEXT, duration_minutes INTEGER, channel_id TEXT, "
                       "message_id TEXT, discord_event_id TEXT, created_by TEXT, created_at TEXT)")
            db.commit()
        asyncio.run(test_commands(database_path))
    print("QoL command paths passed")
