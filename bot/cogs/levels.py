from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID
from db import all_rows, connect, decoded, one, settings
from utils.embeds import render


def level_from_xp(xp: int, base: int, multiplier: float) -> int:
    level = 0
    remaining = xp
    while level < 1000:
        cost = round(base * multiplier ** level)
        if remaining < cost:
            break
        remaining -= cost
        level += 1
    return level


class Levels(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild or message.guild.id != GUILD_ID or message.author.bot:
            return
        config = settings("level_config")
        if not config or str(message.channel.id) in decoded(config["ignored_channel_ids_json"], []):
            return
        if isinstance(message.author, discord.Member) and any(
            str(role.id) in decoded(config["ignored_role_ids_json"], []) for role in message.author.roles
        ):
            return
        now = datetime.now(timezone.utc)
        row = one("SELECT * FROM level_users WHERE guild_id = ? AND user_id = ?",
                  (str(GUILD_ID), str(message.author.id)))
        if row and row["last_xp_at"]:
            previous = datetime.fromisoformat(row["last_xp_at"])
            if (now - previous).total_seconds() < config["cooldown_seconds"]:
                return
        previous_level = row["level"] if row else 0
        xp = (row["xp"] if row else 0) + config["xp_per_message"]
        level = level_from_xp(xp, config["base_xp"], config["multiplier"])
        with connect() as db:
            db.execute("INSERT INTO level_users (guild_id, user_id, xp, level, last_xp_at) VALUES (?, ?, ?, ?, ?) "
                       "ON CONFLICT(guild_id, user_id) DO UPDATE SET xp=excluded.xp, level=excluded.level, "
                       "last_xp_at=excluded.last_xp_at",
                       (str(GUILD_ID), str(message.author.id), xp, level, now.isoformat()))
        if level <= previous_level:
            return
        if isinstance(message.author, discord.Member):
            for mapping in all_rows("SELECT * FROM level_roles WHERE guild_id = ? AND level > ? AND level <= ?",
                                    (str(GUILD_ID), previous_level, level)):
                role = message.guild.get_role(int(mapping["role_id"]))
                if role:
                    await message.author.add_roles(role, reason="Level reward")
        channel = message.guild.get_channel(int(config["announcement_channel_id"])) if config["announcement_channel_id"] else None
        if isinstance(channel, discord.TextChannel):
            template = decoded(config["levelup_embed_json"], {})
            if template.get("title") or template.get("description"):
                await channel.send(embed=render(template, message.guild, message.author, level))

    @app_commands.command(name="rank", description="Show your rank or another member's rank")
    @app_commands.describe(user="Member to check (default: yourself)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        row = one("SELECT * FROM level_users WHERE guild_id = ? AND user_id = ?",
                  (str(GUILD_ID), str(target.id)))
        await interaction.response.send_message(
            f"**{target.display_name}** — Level {row['level'] if row else 0} — "
            f"{row['xp'] if row else 0} XP", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the top 10 members by XP")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        rows = all_rows("SELECT * FROM level_users WHERE guild_id = ? ORDER BY xp DESC LIMIT 10", (str(GUILD_ID),))
        content = "\n".join(f"{i}. <@{r['user_id']}> — Level {r['level']} — {r['xp']} XP"
                            for i, r in enumerate(rows, 1))
        await interaction.response.send_message(
            f"**Top 10 members by XP**\n{content}" if content else "No ranks yet.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Levels(bot))
