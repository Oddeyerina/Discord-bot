from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID


POLL_DURATIONS = (
    ("1 hour", 60), ("4 hours", 240), ("8 hours", 480),
    ("1 day", 1440), ("3 days", 4320), ("7 days", 10080),
)


class Polls(commands.Cog):
    @app_commands.command(name="poll", description="Create a poll in this channel")
    @app_commands.describe(
        question="The poll question", option1="First answer option", option2="Second answer option",
        option3="Third answer option", option4="Fourth answer option", option5="Fifth answer option",
        option6="Sixth answer option", option7="Seventh answer option", option8="Eighth answer option",
        option9="Ninth answer option", option10="Tenth answer option",
        duration="How long the poll stays open", multi="Allow multiple answers")
    @app_commands.choices(duration=[app_commands.Choice(name=name, value=minutes)
                                    for name, minutes in POLL_DURATIONS])
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str,
                   option3: str | None = None, option4: str | None = None,
                   option5: str | None = None, option6: str | None = None,
                   option7: str | None = None, option8: str | None = None,
                   option9: str | None = None, option10: str | None = None,
                   duration: int = 60, multi: bool = False) -> None:
        question = question.strip()
        answers = [answer.strip() for answer in (option1, option2, option3, option4, option5,
                                                  option6, option7, option8, option9, option10)
                   if answer is not None]
        if not 1 <= len(question) <= 300:
            await interaction.response.send_message("The question must contain 1 to 300 characters.", ephemeral=True)
            return
        if any(not 1 <= len(answer) <= 55 for answer in answers):
            await interaction.response.send_message("Each answer must contain 1 to 55 characters.", ephemeral=True)
            return
        if duration == 15:
            await interaction.response.send_message(
                "Discord's native polls require at least one hour. Choose a longer duration.", ephemeral=True)
            return
        poll = discord.Poll(question, timedelta(minutes=duration), multiple=multi)
        for answer in answers:
            poll.add_answer(text=answer)
        await interaction.response.send_message(poll=poll)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Polls())
