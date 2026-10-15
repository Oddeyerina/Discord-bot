"""Check native moderation audit matching and slash-command deduplication."""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


async def check_actions() -> None:
    from cogs import moderation

    bot = SimpleNamespace(user=SimpleNamespace(id=900, display_name="Test bot"))
    cog = moderation.Moderation(bot)
    guild = SimpleNamespace(id=moderation.GUILD_ID)
    user = SimpleNamespace(id=42, mention="<@42>")
    moderator = SimpleNamespace(id=77, mention="<@77>")
    reports: list[tuple] = []

    async def report(*args: object) -> None:
        reports.append(args)

    async def no_entry(*args: object) -> tuple[None, bool]:
        return None, True

    cog.report = report
    moderation.settings = lambda _: {"log_channel_id": "123", "log_mod_actions": True}
    cog.audit_action = no_entry

    await cog.on_member_remove(SimpleNamespace(guild=guild, id=user.id))
    assert not reports, "An ordinary departure must not be logged as a kick"

    entry = SimpleNamespace(user=moderator, reason="Rule violation")

    async def matched(*args: object) -> tuple[object, bool]:
        return entry, True

    cog.audit_action = matched
    await cog.log_native_action(guild, user, "kick", "Member kicked",
                                moderation.discord.AuditLogAction.kick, True)
    assert len(reports) == 1 and reports[0][3] is moderator
    assert reports[0][4] == "Rule violation"

    cog.remember_action(guild, "kick", user)
    await cog.log_native_action(guild, user, "kick", "Member kicked",
                                moderation.discord.AuditLogAction.kick, True)
    assert len(reports) == 1, "A bot-command kick must not log twice"

    async def unavailable(*args: object) -> tuple[None, bool]:
        return None, False

    cog.audit_action = unavailable
    await cog.log_native_action(guild, user, "ban", "Member banned",
                                moderation.discord.AuditLogAction.ban)
    assert len(reports) == 2 and reports[-1][3] is None
    assert reports[-1][4] == "No reason provided"

    cog.audit_action = matched
    entry.user = bot.user
    await cog.log_native_action(guild, user, "unban", "Member unbanned",
                                moderation.discord.AuditLogAction.unban)
    assert len(reports) == 2, "Bot-authored audit entries are already logged by commands"

    entry.user = moderator
    before = SimpleNamespace(guild=guild, id=user.id, communication_disabled_until=None)
    after = SimpleNamespace(guild=guild, id=user.id,
                            communication_disabled_until=datetime(2099, 1, 1, tzinfo=timezone.utc))
    await cog.on_member_update(before, after)
    assert reports[-1][1] == "Member timed out"


if __name__ == "__main__":
    os.environ["DISCORD_GUILD_ID"] = "123456789"
    os.environ["DISCORD_TOKEN"] = "test-token"
    os.environ["DATABASE_URL"] = "sqlite:///test.db"
    sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))
    asyncio.run(check_actions())
    print("Native moderation paths passed")
