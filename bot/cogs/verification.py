"""Persistent rules acceptance button and rules panel publishing."""

import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID
from db import connect, decoded, settings
from utils.embeds import render
from utils.safe import safe_delete, safe_edit, safe_send


class RulesView(discord.ui.View):
    def __init__(self, label: str = "I agree to the rules") -> None:
        super().__init__(timeout=None)
        button = discord.ui.Button(label=label[:80], style=discord.ButtonStyle.success,
                                   custom_id="verify:agree")
        button.callback = self.agree
        self.add_item(button)

    async def agree(self, interaction: discord.Interaction) -> None:
        config = settings("verification_config")
        if not config or not config["enabled"] or not config["verified_role_id"] or not interaction.guild:
            await interaction.response.send_message("Verification is unavailable.", ephemeral=True)
            return
        role = interaction.guild.get_role(int(config["verified_role_id"]))
        if role is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("The verified role is unavailable.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("You are already verified.", ephemeral=True)
            return
        await interaction.user.add_roles(role, reason="Accepted server rules")
        await interaction.response.send_message("You are verified. Welcome!", ephemeral=True)


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def post_rules(self, resend: bool = False) -> None:
        config = settings("verification_config")
        guild = self.bot.get_guild(GUILD_ID)
        if not config or not config["enabled"] or not config["rules_channel_id"] or not guild:
            raise ValueError("Configure and enable rules verification first")
        channel = guild.get_channel(int(config["rules_channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            raise ValueError("The rules channel is unavailable")
        embed = render(decoded(config["rules_embed_json"], {}), guild)
        view = RulesView(config["button_label"])
        if config["rules_message_id"] and resend:
            try:
                old = await channel.fetch_message(int(config["rules_message_id"]))
                if not await safe_delete(old):
                    raise RuntimeError("Could not replace the previous rules message")
            except discord.NotFound:
                pass
        if config["rules_message_id"] and not resend:
            try:
                message = await channel.fetch_message(int(config["rules_message_id"]))
                if not await safe_edit(message, embed=embed, view=view):
                    raise RuntimeError("Could not update the rules message")
                return
            except discord.NotFound:
                pass
        message = await safe_send(channel, embed=embed, view=view)
        if message is None:
            raise RuntimeError("Could not post the rules message")
        with connect() as db:
            db.execute("UPDATE verification_config SET rules_message_id = ? WHERE guild_id = ?",
                       (str(message.id), str(GUILD_ID)))

    @app_commands.command(name="post-rules", description="Post or update the rules panel")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def post_rules_command(self, interaction: discord.Interaction) -> None:
        config = settings("verification_config")
        if not config or str(interaction.channel_id) != config["rules_channel_id"]:
            await interaction.response.send_message("Use this command in the configured rules channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            await self.post_rules()
        except (ValueError, RuntimeError) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        await interaction.followup.send("Rules panel posted or updated.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    bot.add_view(RulesView())
    await bot.add_cog(Verification(bot))
