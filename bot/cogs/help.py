import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID


CATEGORIES = {
    "Levels": ("rank", "leaderboard"),
    "Birthdays": ("birthday set", "birthday remove", "birthday list"),
    "Voice": ("tempvoice name", "tempvoice limit", "tempvoice lock", "tempvoice unlock",
              "tempvoice claim", "tempvoice delete"),
    "Community": ("poll", "event create", "event list", "event cancel"),
    "Info": ("userinfo", "serverinfo", "help"),
}


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Show available member commands")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def help_command(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="Available Commands", color=discord.Color.blurple())
        guild = discord.Object(id=GUILD_ID)
        for category, paths in CATEGORIES.items():
            lines: list[str] = []
            for path in paths:
                names = path.split()
                command = self.bot.tree.get_command(names[0], guild=guild)
                if command is None:
                    continue
                if len(names) == 2 and isinstance(command, app_commands.Group):
                    command = command.get_command(names[1])
                if command is not None:
                    lines.append(f"`/{path}` — {command.description}")
            if lines:
                embed.add_field(name=category, value="\n".join(lines), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
