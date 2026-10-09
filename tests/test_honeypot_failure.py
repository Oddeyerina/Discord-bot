"""A Discord moderation failure should be logged without stopping the cog."""

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import discord

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("SESSION_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/dcbot.db")
sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))

import cogs.honeypot as honeypot  # noqa: E402


async def test_failed_action() -> None:
    class Member:
        id = 888
        bot = False
        roles: list = []
        guild_permissions = SimpleNamespace(administrator=False)

        async def ban(self, *, reason: str) -> None:
            response = SimpleNamespace(status=403, reason="Forbidden")
            raise discord.Forbidden(response, "Target has a higher role")

    config = {"channel_id": "999", "action": "ban", "delete_message": False,
              "dm_user": False, "whitelist_role_ids_json": "[]"}
    with patch.object(honeypot, "settings", return_value=config), patch.object(honeypot.log, "warning") as warning:
        await honeypot.Honeypot(None).trigger(Member(), SimpleNamespace(id=999))
        warning.assert_called_once()


if __name__ == "__main__":
    asyncio.run(test_failed_action())
    print("Honeypot failure handled")
