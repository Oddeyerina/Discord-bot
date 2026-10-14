import discord
from discord.ext import commands

from config import GUILD_ID
from db import all_rows, decoded, one


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def handle_reaction(self, payload: discord.RawReactionActionEvent, add: bool) -> None:
        if payload.guild_id != GUILD_ID:
            return
        panel = one("SELECT * FROM panels WHERE guild_id = ? AND type = 'reactionroles' "
                    "AND active = 1 AND message_id = ?",
                    (str(GUILD_ID), str(payload.message_id)))
        if not panel or decoded(panel["extra_config_json"], {}).get("style", "reaction") != "reaction":
            return
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(payload.user_id) if guild else None
        if member is None and guild is not None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return
        if not member or member.bot:
            return
        for row in all_rows("SELECT * FROM reaction_roles WHERE panel_id = ?", (panel["id"],)):
            if row["emoji"] == str(payload.emoji):
                role = guild.get_role(int(row["role_id"]))
                if role:
                    if add:
                        await member.add_roles(role, reason="Reaction role")
                    else:
                        await member.remove_roles(role, reason="Reaction role")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        await self.handle_reaction(payload, True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        await self.handle_reaction(payload, False)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id != GUILD_ID or not interaction.data:
            return
        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("roles:select:") or not isinstance(interaction.user, discord.Member):
            return
        panel_id = int(custom_id.rsplit(":", 1)[1])
        panel = one("SELECT id FROM panels WHERE id = ? AND guild_id = ? AND type = 'reactionroles' "
                    "AND active = 1 AND message_id = ?",
                    (panel_id, str(GUILD_ID), str(interaction.message.id) if interaction.message else ""))
        if panel is None:
            await interaction.response.send_message("This role panel is no longer available.", ephemeral=True)
            return
        rows = all_rows("SELECT * FROM reaction_roles WHERE panel_id = ?", (panel_id,))
        selected = set(interaction.data.get("values", []))
        for row in rows:
            role = interaction.guild.get_role(int(row["role_id"])) if interaction.guild else None
            if role:
                if str(row["id"]) in selected and role not in interaction.user.roles:
                    await interaction.user.add_roles(role, reason="Role select")
                elif str(row["id"]) not in selected and role in interaction.user.roles:
                    await interaction.user.remove_roles(role, reason="Role select")
        await interaction.response.send_message("Your roles were updated.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReactionRoles(bot))
