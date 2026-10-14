"""Sticky messages are deleted and reposted, never pinned or edited."""

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import discord

os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/dcbot.db")
os.environ.setdefault("SESSION_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))

from cogs import sticky  # noqa: E402


class FakeMessage:
    def __init__(self, message_id: int) -> None:
        self.id = message_id
        self.deleted = False
        self.delete_forbidden = False

    async def delete(self) -> None:
        if self.delete_forbidden:
            raise discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), "Missing Access")
        self.deleted = True


class FakeChannel:
    id = 456

    def __init__(self) -> None:
        self.messages: dict[int, FakeMessage] = {}
        self.sends: list[dict] = []
        self.forbidden = False

    async def fetch_message(self, message_id: int) -> FakeMessage:
        if message_id not in self.messages:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "Missing")
        return self.messages[message_id]

    async def send(self, **kwargs: object) -> FakeMessage:
        if self.forbidden:
            raise discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), "Missing Access")
        self.sends.append(kwargs)
        message = FakeMessage(100 + len(self.sends))
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


async def test_sticky_repost() -> None:
    row = {"id": 1, "enabled": True, "sticky_message_id": None,
           "last_sticky_at": None, "cooldown_seconds": 0,
           "role_id": "789", "sticky_embed_json": '{"title":"Sticky {role}"}'}
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
        assert len(channel.sends) == 1 and row["sticky_message_id"] == "101"
        assert channel.sends[0]["content"] == "<@&789>"
        await cog.post_sticky("456")
        assert first.deleted and len(channel.sends) == 2
        assert row["sticky_message_id"] == "102"
        del channel.messages[102]
        await cog.post_sticky("456", force=True)
        assert len(channel.sends) == 3 and row["sticky_message_id"] == "103"
        channel.messages[103].delete_forbidden = True
        try:
            await cog.post_sticky("456", force=True)
        except ValueError as exc:
            assert str(exc) == "The bot cannot access this channel. Check permissions."
        else:
            raise AssertionError("Failed deletion must not create a duplicate sticky")
        assert len(channel.sends) == 3
        channel.messages[103].delete_forbidden = False
        channel.forbidden = True
        try:
            await cog.post_sticky("456", force=True)
        except ValueError as exc:
            assert str(exc) == "The bot cannot access this channel. Check permissions."
        else:
            raise AssertionError("Inaccessible channel must report a permission error")
    finally:
        sticky.one, sticky.connect = original_one, original_connect
        sticky.discord.TextChannel = original_channel_type


if __name__ == "__main__":
    asyncio.run(test_sticky_repost())
    print("Sticky repost behavior passed")
