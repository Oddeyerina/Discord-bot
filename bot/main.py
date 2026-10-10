import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_TOKEN, GUILD_ID
from sync import sync_guild_data
from tasks import process_tasks
from utils.logger import configure

configure()
log = logging.getLogger(__name__)


class SuiteBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.reactions = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.tasks_started = False
        self.tree.on_error = self.on_app_command_error

    async def on_app_command_error(self, interaction: discord.Interaction,
                                   error: app_commands.AppCommandError) -> None:
        log.error("Slash command failed: %s", interaction.command,
                  exc_info=(type(error), error, error.__traceback__))
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"This command is on cooldown. Try again in {error.retry_after:.1f} seconds."
        elif isinstance(error, app_commands.MissingPermissions):
            message = "You do not have the required permissions to use this command."
        else:
            message = "Something went wrong. The error has been logged."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            log.exception("Could not send slash command error response")

    async def setup_hook(self) -> None:
        for cog in ("tickets", "honeypot", "reaction_roles", "levels", "welcome",
                    "sticky", "tempvoice", "stickyroles", "remembering", "help", "info",
                    "poll", "events"):
            await self.load_extension(f"cogs.{cog}")
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))

    async def on_ready(self) -> None:
        log.info("Connected as %s", self.user)
        if not self.tasks_started:
            self.tasks_started = True
            asyncio.create_task(process_tasks(self))
            asyncio.create_task(self.periodic_sync())

    async def periodic_sync(self) -> None:
        while not self.is_closed():
            try:
                await sync_guild_data(self)
            except Exception:
                log.exception("Guild data sync failed")
            await asyncio.sleep(300)


if __name__ == "__main__":
    SuiteBot().run(DISCORD_TOKEN)
