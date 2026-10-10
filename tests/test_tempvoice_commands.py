"""Exercise temporary voice ownership and channel command boundaries without Discord I/O."""

import asyncio
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import discord


class FakeUser:
    def __init__(self, user_id: int, channel: object) -> None:
        self.id = user_id
        self.voice = SimpleNamespace(channel=channel)


class FakeRole:
    id = 0


class FakeChannel:
    id = 777

    def __init__(self, default_role: object) -> None:
        self.default_role = default_role
        self.members: list[FakeUser] = []
        self.overwrites: dict[object, discord.PermissionOverwrite] = {
            default_role: discord.PermissionOverwrite(view_channel=False)
        }
        self.name = "Temporary"
        self.user_limit = 0
        self.deleted = False

    async def edit(self, **kwargs: object) -> None:
        self.name = kwargs.get("name", self.name)
        self.user_limit = kwargs.get("user_limit", self.user_limit)
        self.overwrites = kwargs.get("overwrites", self.overwrites)

    def overwrites_for(self, target: object) -> discord.PermissionOverwrite:
        return self.overwrites.get(target, discord.PermissionOverwrite())

    async def set_permissions(self, target: object, *, overwrite: discord.PermissionOverwrite,
                              reason: str) -> None:
        self.overwrites[target] = overwrite

    async def delete(self, *, reason: str) -> None:
        self.deleted = True


class FakeResponse:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.deferred = False

    async def send_message(self, content: str, *, ephemeral: bool) -> None:
        assert ephemeral
        self.messages.append(content)

    async def defer(self, *, ephemeral: bool) -> None:
        assert ephemeral
        self.deferred = True


async def test_commands() -> None:
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "voice.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["DISCORD_TOKEN"] = "test-token"
        os.environ["DISCORD_GUILD_ID"] = "123456789"
        os.environ["SESSION_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
        sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))
        import cogs.tempvoice as tempvoice

        with closing(sqlite3.connect(database_path)) as db:
            db.execute("CREATE TABLE tempvoice_active (id INTEGER PRIMARY KEY, guild_id TEXT, "
                       "channel_id TEXT, owner_id TEXT, created_at DATETIME)")
            db.execute("INSERT INTO tempvoice_active VALUES (1, '123456789', '777', '888', '')")
            db.commit()

        original_channel = tempvoice.discord.VoiceChannel
        tempvoice.discord.VoiceChannel = FakeChannel
        try:
            default_role = FakeRole()
            channel = FakeChannel(default_role)
            owner = FakeUser(888, channel)
            guest = FakeUser(999, channel)
            channel.members = [owner, guest]
            channel.overwrites[owner] = discord.PermissionOverwrite(manage_channels=True)
            guild = SimpleNamespace(default_role=default_role,
                                    get_channel=lambda channel_id: channel if channel_id == 777 else None)

            def interaction(user: FakeUser, channel_id: int = 777) -> SimpleNamespace:
                response = FakeResponse()
                return SimpleNamespace(guild_id=123456789, guild=guild, channel_id=channel_id,
                                       user=user, response=response,
                                       followup=SimpleNamespace(send=response.send_message))

            cog = tempvoice.TempVoice(None)
            outsider = interaction(guest)
            await cog.rename.callback(cog, outsider, "New name")
            assert outsider.response.messages == ["Only the channel owner can do that."]
            assert channel.name == "Temporary"

            elsewhere = interaction(owner, channel_id=123)
            await cog.rename.callback(cog, elsewhere, "New name")
            assert elsewhere.response.messages == ["Use this command in a temporary voice channel."]

            too_long = interaction(owner)
            await cog.rename.callback(cog, too_long, "x" * 101)
            assert "1 to 100" in too_long.response.messages[0]
            await cog.rename.callback(cog, interaction(owner), "New name")
            assert channel.name == "New name"

            invalid_limit = interaction(owner)
            await cog.limit.callback(cog, invalid_limit, 100)
            assert "0 and 99" in invalid_limit.response.messages[0]
            await cog.limit.callback(cog, interaction(owner), 0)
            assert channel.user_limit == 0

            await cog.unlock.callback(cog, interaction(owner))
            assert channel.overwrites[default_role].connect is True
            assert channel.overwrites[default_role].view_channel is True
            await cog.lock.callback(cog, interaction(owner))
            assert channel.overwrites[default_role].connect is False

            owner_present = interaction(guest)
            await cog.claim.callback(cog, owner_present)
            assert "still in this channel" in owner_present.response.messages[0]
            channel.members = [guest]
            await cog.claim.callback(cog, interaction(guest))
            with closing(sqlite3.connect(database_path)) as db:
                assert db.execute("SELECT owner_id FROM tempvoice_active WHERE id = 1").fetchone()[0] == "999"
            assert owner not in channel.overwrites
            assert channel.overwrites[guest].manage_channels is True

            await cog.delete.callback(cog, interaction(guest))
            assert channel.deleted
            with closing(sqlite3.connect(database_path)) as db:
                assert db.execute("SELECT id FROM tempvoice_active").fetchone() is None
        finally:
            tempvoice.discord.VoiceChannel = original_channel


if __name__ == "__main__":
    asyncio.run(test_commands())
    print("Temp voice commands passed")
