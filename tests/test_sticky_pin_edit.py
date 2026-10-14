"""A sticky is pinned once, edited in place, and recreated if deleted."""

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import discord

os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/dcbot.db")
os.environ.setdefault("SESSION_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))

from cogs import sticky  # noqa: E402


class FakeMessage:
    def __init__(self, message_id: int, pin_fails: bool = False) -> None:
        self.id = message_id
        self.pin_fails = pin_fails
        self.pins = 0
        self.edits: list[dict] = []

    async def pin(self, **_: object) -> None:
        self.pins += 1
        if self.pin_fails:
            raise discord.HTTPException(SimpleNamespace(status=400, reason="Bad Request"),
                                        "Maximum pins reached")

    async def edit(self, **kwargs: object) -> None:
        self.edits.append(kwargs)


class FakeChannel:
    id = 456

    def __init__(self) -> None:
        self.messages: dict[int, FakeMessage] = {}
        self.sends: list[dict] = []
        self.pin_fails = False

    async def fetch_message(self, message_id: int) -> FakeMessage:
        if message_id not in self.messages:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "Missing")
        return self.messages[message_id]

    async def send(self, **kwargs: object) -> FakeMessage:
        self.sends.append(kwargs)
        message = FakeMessage(100 + len(self.sends), self.pin_fails)
        self.messages[message.id] = message
        return message


class FakeConnection:
    def __init__(self, row: dict) -> None:
        self.row = row

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def execute(self, _: str, values: tuple[str, str, int]) -> None:
        self.row["sticky_message_id"], self.row["last_sticky_at"], _ = values


async def test_sticky_pin_edit() -> None:
    row = {"id": 1, "enabled": True, "sticky_message_id": None,
           "last_sticky_at": None, "cooldown_seconds": 0,
           "role_id": "789", "sticky_embed_json": '{"title":"Sticky"}'}
    role = SimpleNamespace(id=789, mention="<@&789>")
    channel = FakeChannel()
    guild = SimpleNamespace(name="Test", member_count=1, text_channels=[], forum_channels=[],
                            roles=[], get_role=lambda _: role, get_channel=lambda _: channel)
    bot = SimpleNamespace(get_guild=lambda _: guild)
    original_one, original_connect = sticky.one, sticky.connect
    original_channel_type = sticky.discord.TextChannel
    sticky.one = lambda *_: row
    sticky.connect = lambda: FakeConnection(row)
    sticky.discord.TextChannel = FakeChannel
    try:
        cog = sticky.Sticky(bot)
        await cog.post_sticky("456")
        first = channel.messages[101]
        assert first.pins == 1 and len(channel.sends) == 1
        assert row["sticky_message_id"] == "101"
        await cog.post_sticky("456")
        assert len(channel.sends) == 1 and first.pins == 1 and len(first.edits) == 1
        assert first.edits[0]["allowed_mentions"].roles is False
        assert first.edits[0]["allowed_mentions"].users is False
        await cog.post_sticky("456", force=True, ping_on_edit=True)
        assert len(first.edits) == 2 and first.edits[1]["allowed_mentions"].roles == [role]
        del channel.messages[101]
        channel.pin_fails = True
        with patch.object(sticky.log, "warning") as warning:
            await cog.post_sticky("456", force=True)
            warning.assert_called_once()
        assert len(channel.sends) == 2 and channel.messages[102].pins == 1
        assert row["sticky_message_id"] == "102"
    finally:
        sticky.one, sticky.connect = original_one, original_connect
        sticky.discord.TextChannel = original_channel_type


if __name__ == "__main__":
    asyncio.run(test_sticky_pin_edit())
    print("Sticky pin and edit behavior passed")
