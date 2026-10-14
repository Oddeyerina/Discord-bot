"""Check stats counters and embed placeholder rendering without Discord access."""

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

from cogs.stats import stats_values  # noqa: E402
from utils.embeds import render  # noqa: E402


def test_stats() -> None:
    artist = SimpleNamespace(id=123, mention="<@&123>", name="Artist")
    online = SimpleNamespace(bot=False, status=discord.Status.online, voice=None, roles=[artist])
    offline = SimpleNamespace(bot=False, status=discord.Status.offline,
                              voice=SimpleNamespace(channel=object()), roles=[])
    bot_member = SimpleNamespace(bot=True, status=discord.Status.online, voice=None, roles=[])
    guild = SimpleNamespace(
        name="Test Server", member_count=3, members=[online, offline, bot_member],
        premium_subscription_count=1, premium_tier=1, premium_subscribers=[],
        get_role=lambda role_id: artist if role_id == 123 else None,
        text_channels=[SimpleNamespace(name="general", mention="<#456>")],
        forum_channels=[], roles=[artist],
    )
    values = stats_values(guild, [{"label": "Artists", "role_id": "123"}])
    assert values["total_members"] == "3"
    assert values["human_members"] == "2"
    assert values["bot_members"] == "1"
    assert values["online"] == "2"
    assert values["in_voice"] == "1"
    assert values["artist_count"] == "1"
    assert values["role_count_artists"] == "1"
    assert values["boosts_needed"] == "6"
    embed = render({"title": "Members: {total_members}",
                    "description": "#general @Artist {role_count_artists} {timestamp}",
                    "footer": "In {guild}"}, guild, stats=values)
    assert embed.title == "Members: 3"
    assert "<#456> <@&123> 1 <t:" in embed.description
    assert embed.footer.text == "In Test Server"


if __name__ == "__main__":
    test_stats()
    print("Stats values and embed rendering passed")
