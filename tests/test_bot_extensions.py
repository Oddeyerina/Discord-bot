"""Load all bot cogs without connecting to Discord."""

import asyncio
import os
import sys
from pathlib import Path

import discord

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("DISCORD_GUILD_ID", "123456789")
os.environ.setdefault("SESSION_SECRET", "test-secret-0123456789abcdef0123456789abcdef")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/dcbot.db")
sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))

from main import SuiteBot  # noqa: E402


async def test_extensions() -> None:
    bot = SuiteBot()
    for cog in ("tickets", "honeypot", "reaction_roles", "levels", "welcome",
                "sticky", "tempvoice", "stickyroles", "remembering"):
        await bot.load_extension(f"cogs.{cog}")
    assert len(bot.cogs) == 9
    guild_commands = {command.name: command for command in bot.tree.get_commands(guild=discord.Object(id=123456789))}
    assert {"birthday", "rank", "leaderboard", "tempvoice"} <= guild_commands.keys()
    assert {command.name for command in guild_commands["birthday"].commands} == {"set", "remove", "list"}
    assert {command.name for command in guild_commands["tempvoice"].commands} == {
        "name", "limit", "lock", "unlock", "claim", "delete"}
    for command in guild_commands.values():
        assert command.description[0].isupper() and not command.description.endswith(".")
        if hasattr(command, "commands"):
            for subcommand in command.commands:
                assert subcommand.description[0].isupper() and not subcommand.description.endswith(".")
                assert all(parameter.description[0].isupper() and
                           not parameter.description.endswith(".") for parameter in subcommand.parameters)
        else:
            assert all(parameter.description[0].isupper() and
                       not parameter.description.endswith(".") for parameter in command.parameters)

    set_date = next(command for command in guild_commands["birthday"].commands if command.name == "set")
    set_options = {option["name"]: option for option in set_date.to_dict(bot.tree)["options"]}
    assert (set_options["day"]["min_value"], set_options["day"]["max_value"]) == (1, 31)
    assert (set_options["year"]["min_value"], set_options["year"]["max_value"]) == (1900, 2100)
    assert [choice["name"] for choice in set_options["month"]["choices"]] == [
        "January", "February", "March", "April", "May", "June", "July", "August",
        "September", "October", "November", "December"]
    limit = next(command for command in guild_commands["tempvoice"].commands if command.name == "limit")
    limit_option = limit.to_dict(bot.tree)["options"][0]
    assert limit_option["name"] == "limit"
    assert (limit_option["min_value"], limit_option["max_value"]) == (0, 99)

    synced_payload: list[dict] = []

    async def fake_upsert(application_id: int, guild_id: int, *, payload: list[dict]) -> list[dict]:
        assert application_id == 123456789 and guild_id == 123456789
        synced_payload.extend(payload)
        return []

    bot._connection.application_id = 123456789
    bot.tree._http.bulk_upsert_guild_commands = fake_upsert
    await bot.tree.sync(guild=discord.Object(id=123456789))
    assert {command["name"] for command in synced_payload} == guild_commands.keys()
    await bot.close()


if __name__ == "__main__":
    asyncio.run(test_extensions())
    print("Bot extensions loaded and guild command sync payload validated")
