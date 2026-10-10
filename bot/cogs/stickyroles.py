import json
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import GUILD_ID
from db import connect, decoded, one, settings

log = logging.getLogger(__name__)


class StickyRoles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID or member.bot:
            return
        config = settings("sticky_roles_config")
        if not config or not config["enabled"]:
            return
        excluded = set(decoded(config["excluded_role_ids_json"], []))
        ids = [str(role.id) for role in member.roles if not role.is_default() and
               not role.managed and not role.is_bot_managed() and str(role.id) not in excluded]
        with connect() as db:
            db.execute("INSERT INTO sticky_roles_saved (guild_id, user_id, role_ids_json, saved_at) "
                       "VALUES (?, ?, ?, ?) ON CONFLICT(guild_id, user_id) DO UPDATE SET "
                       "role_ids_json = excluded.role_ids_json, saved_at = excluded.saved_at",
                       (str(GUILD_ID), str(member.id), json.dumps(ids), datetime.now(timezone.utc).isoformat()))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild.id != GUILD_ID or member.bot:
            return
        config = settings("sticky_roles_config")
        saved = one("SELECT role_ids_json FROM sticky_roles_saved WHERE guild_id = ? AND user_id = ?",
                    (str(GUILD_ID), str(member.id)))
        if not config or not config["enabled"] or not saved:
            return
        excluded = set(decoded(config["excluded_role_ids_json"], []))
        roles = [role for value in decoded(saved["role_ids_json"], [])
                 if value not in excluded and (role := member.guild.get_role(int(value))) is not None
                 and not role.managed and role.is_assignable()]
        if roles:
            try:
                await member.add_roles(*roles, reason="Restore saved roles")
            except (discord.Forbidden, discord.HTTPException):
                log.exception("Could not restore roles for %s", member.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StickyRoles(bot))
