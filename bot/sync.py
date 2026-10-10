import logging

import discord
import httpx

from config import API_BASE_URL, GUILD_ID, SESSION_SECRET

log = logging.getLogger(__name__)


async def sync_guild_data(bot: discord.Client) -> None:
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        log.warning("Configured guild is not available")
        return
    payload = {
        "guild_id": str(GUILD_ID),
        "channels": [{"id": str(c.id), "name": c.name, "type": str(c.type)}
                     for c in guild.channels if isinstance(c, (discord.TextChannel, discord.VoiceChannel,
                                                              discord.CategoryChannel))],
        "roles": [{"id": str(r.id), "name": r.name, "position": r.position}
                  for r in guild.roles if not r.is_default()],
        "emojis": [{"id": str(e.id), "name": e.name, "animated": e.animated}
                   for e in guild.emojis],
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"{API_BASE_URL}/internal/guild-sync", json=payload,
                                     headers={"X-Internal-Secret": SESSION_SECRET})
        response.raise_for_status()
