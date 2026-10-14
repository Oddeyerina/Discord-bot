import re
from typing import Any

import discord


def render(template: dict[str, Any], guild: discord.Guild | None = None,
           user: discord.abc.User | None = None, level: int | None = None,
           label: str = "", age: int | None = None,
           role: discord.Role | None = None,
           stats: dict[str, str] | None = None) -> discord.Embed:
    values = {"user": user.mention if user else "", "guild": guild.name if guild else "",
              "membercount": str(guild.member_count or 0) if guild else "0",
              "level": str(level or 0), "label": label, "age": str(age) if age is not None else "",
              "role": role.mention if role else ""}
    values.update(stats or {})

    def expand(value: str) -> str:
        result = re.sub(r"\{([a-z][a-z0-9_]*)\}",
                        lambda match: values.get(match.group(1), match.group(0)), value)
        if guild is None:
            return result
        channels = [*getattr(guild, "text_channels", []), *getattr(guild, "forum_channels", [])]
        for channel in sorted(channels, key=lambda item: len(item.name), reverse=True):
            result = re.sub(re.escape(f"#{channel.name}"), f"<#{channel.id}>", result,
                            flags=re.IGNORECASE)
        for guild_role in sorted(getattr(guild, "roles", []), key=lambda item: len(item.name),
                                 reverse=True):
            if guild_role.name != "@everyone":
                result = re.sub(re.escape(f"@{guild_role.name}"), f"<@&{guild_role.id}>",
                                result, flags=re.IGNORECASE)
        return result

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
