"""Voice XP timers start only for eligible pairs and stop when a member leaves."""

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/dcbot.db")
os.environ.setdefault("SESSION_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))

import cogs.levels as levels  # noqa: E402


async def test_tracking() -> None:
    original_settings = levels.settings
    levels.settings = lambda _: {"voice_xp_per_minute": 5, "voice_ignored_channel_ids_json": "[]"}
    try:
        guild = SimpleNamespace(afk_channel=None)
        channel = SimpleNamespace(id=42, members=[])
        first = SimpleNamespace(id=1, bot=False, guild=guild, voice=SimpleNamespace(channel=channel))
        second = SimpleNamespace(id=2, bot=False, guild=guild, voice=SimpleNamespace(channel=channel))
        cog = levels.Levels(SimpleNamespace())
        channel.members = [first]
        cog._reconcile_voice(first, channel, guild)
        assert cog._voice_tasks == {}
        channel.members = [first, second]
        cog._reconcile_voice(first, channel, guild)
        cog._reconcile_voice(second, channel, guild)
        assert set(cog._voice_tasks) == {1, 2}
        channel.members = [first]
        second.voice.channel = None
        cog._reconcile_voice(first, channel, guild)
        cog._cancel_voice(second.id)
        assert cog._voice_tasks == {}
        await asyncio.sleep(0)
    finally:
        levels.settings = original_settings


if __name__ == "__main__":
    asyncio.run(test_tracking())
    print("Voice XP timer eligibility passed")
