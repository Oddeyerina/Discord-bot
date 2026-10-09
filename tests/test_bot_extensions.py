"""Load all bot cogs without connecting to Discord."""

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("SESSION_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/dcbot.db")
sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))

from main import SuiteBot  # noqa: E402


async def test_extensions() -> None:
    bot = SuiteBot()
    for cog in ("tickets", "honeypot", "reaction_roles", "levels", "welcome"):
        await bot.load_extension(f"cogs.{cog}")
    assert len(bot.cogs) == 5
    await bot.close()


if __name__ == "__main__":
    asyncio.run(test_extensions())
    print("Bot extensions loaded")
