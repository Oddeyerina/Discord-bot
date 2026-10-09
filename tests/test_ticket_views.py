"""Verify ticket buttons can be registered for interactions after a restart."""

import asyncio
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("SESSION_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))

from cogs.tickets import done_view, setup, ticket_view  # noqa: E402


async def test_persistent_views() -> None:
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
    await setup(bot)
    assert len(bot.persistent_views) == 2
    assert ticket_view().is_persistent()
    assert done_view().is_persistent()
    assert done_view(disabled=True).children[0].disabled
    await bot.close()


if __name__ == "__main__":
    asyncio.run(test_persistent_views())
    print("Ticket views passed")
