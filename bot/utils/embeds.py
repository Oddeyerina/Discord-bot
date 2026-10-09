import re
from typing import Any

import discord


def render(template: dict[str, Any], guild: discord.Guild | None = None,
           user: discord.abc.User | None = None, level: int | None = None) -> discord.Embed:
    values = {"user": user.mention if user else "", "guild": guild.name if guild else "",
              "membercount": str(guild.member_count or 0) if guild else "0",
              "level": str(level or 0)}

    def expand(value: str) -> str:
        return re.sub(r"\{(user|guild|membercount|level)\}",
                      lambda match: values[match.group(1)], value)

    raw_color = template.get("color", "#5865F2")
    try:
        color = int(str(raw_color).lstrip("#"), 16)
    except ValueError:
        color = 0x5865F2
    embed = discord.Embed(title=expand(template.get("title", "")),
                          description=expand(template.get("description", "")), color=color)
    if template.get("footer"):
        embed.set_footer(text=expand(template["footer"]))
    if template.get("thumbnail"):
        embed.set_thumbnail(url=template["thumbnail"])
    if template.get("image"):
        embed.set_image(url=template["image"])
    return embed
