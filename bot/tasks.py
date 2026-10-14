import asyncio
import logging
from datetime import datetime, timezone

import discord

from config import GUILD_ID
from db import all_rows, connect, decoded, one
from runtime import run_maintenance
from sync import sync_guild_data
from utils.embeds import render
from utils.safe import safe_delete, safe_edit, safe_send

log = logging.getLogger(__name__)


def make_view(panel: dict, guild: discord.Guild) -> discord.ui.View | None:
    view = discord.ui.View(timeout=None)
    kind = panel["type"]
    if kind == "tickets":
        view.add_item(discord.ui.Button(label="Open Ticket", style=discord.ButtonStyle.primary,
                                        custom_id=f"ticket:open:{panel['id']}"))
    elif kind == "reactionroles" and decoded(panel["extra_config_json"], {}).get("style") == "select":
        rows = all_rows("SELECT * FROM reaction_roles WHERE panel_id = ? ORDER BY position", (panel["id"],))
        if rows:
            options = [discord.SelectOption(label=(guild.get_role(int(r["role_id"])).name if guild.get_role(int(r["role_id"])) else f"Role {r['role_id']}"), value=str(r["id"]),
                                            emoji=r["emoji"] or None) for r in rows]
            view.add_item(discord.ui.Select(placeholder="Choose your roles", min_values=0,
                                            max_values=len(options), options=options,
                                            custom_id=f"roles:select:{panel['id']}"))
    return view if view.children else None


async def publish_panel(bot: discord.Client, panel_id: int) -> None:
    panel = one("SELECT * FROM panels WHERE id = ? AND guild_id = ? AND active = 1",
                (panel_id, str(GUILD_ID)))
    if panel is None:
        raise ValueError("Panel not found")
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        raise RuntimeError("Guild unavailable")
    channel = guild.get_channel(int(panel["channel_id"]))
    if not isinstance(channel, discord.TextChannel):
        raise ValueError("Panel channel must be a text channel")
    embed = render(decoded(panel["embed_json"], {}), guild)
    view = make_view(panel, guild)
    message = None
    if panel["message_id"]:
        try:
            message = await channel.fetch_message(int(panel["message_id"]))
            if not await safe_edit(message, embed=embed, view=view):
                raise RuntimeError("Could not update panel message")
            if panel["type"] == "reactionroles":
                await message.clear_reactions()
        except discord.NotFound:
            message = None
    if message is None:
        message = await safe_send(channel, embed=embed, view=view)
        if message is None:
            raise RuntimeError("Could not post panel message")
        with connect() as db:
            db.execute("UPDATE panels SET message_id = ? WHERE id = ?", (str(message.id), panel_id))
    if panel["type"] == "reactionroles" and decoded(panel["extra_config_json"], {}).get("style") == "reaction":
        for row in all_rows("SELECT emoji FROM reaction_roles WHERE panel_id = ? ORDER BY position", (panel_id,)):
            emoji = row["emoji"] or ""
            if not emoji.strip():
                log.warning("Skipping empty emoji for panel %s", panel_id)
                continue
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                log.warning("Skipping invalid emoji %r for panel %s", emoji, panel_id)


async def delete_panel(bot: discord.Client, panel_id: int) -> None:
    panel = one("SELECT * FROM panels WHERE id = ? AND guild_id = ?", (panel_id, str(GUILD_ID)))
    if panel is None or not panel["message_id"]:
        return
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(int(panel["channel_id"])) if guild else None
    if isinstance(channel, discord.TextChannel):
        try:
            message = await channel.fetch_message(int(panel["message_id"]))
            if not await safe_delete(message):
                raise RuntimeError("Could not delete panel message")
        except discord.NotFound:
            pass
    with connect() as db:
        db.execute("UPDATE panels SET message_id = NULL WHERE id = ?", (panel_id,))


async def process_tasks(bot: discord.Client) -> None:
    with connect() as db:
        db.execute("UPDATE bot_tasks SET status = 'pending' WHERE guild_id = ? AND status = 'running'",
                   (str(GUILD_ID),))
    while not bot.is_closed():
        try:
            pending = all_rows("SELECT * FROM bot_tasks WHERE guild_id = ? AND status = 'pending' ORDER BY id LIMIT 10",
                               (str(GUILD_ID),))
            for task in pending:
                with connect() as db:
                    claimed = db.execute("UPDATE bot_tasks SET status = 'running' WHERE id = ? AND status = 'pending'",
                                         (task["id"],)).rowcount
                if not claimed:
                    continue
                error = None
                try:
                    if task["type"] in ("post_panel", "update_panel"):
                        await publish_panel(bot, int(decoded(task["payload_json"], {})["panel_id"]))
                    elif task["type"] == "delete_panel":
                        await delete_panel(bot, int(decoded(task["payload_json"], {})["panel_id"]))
                    elif task["type"] == "sync_guild_data":
                        await sync_guild_data(bot)
                    elif task["type"] == "post_sticky":
                        cog = bot.get_cog("Sticky")
                        if cog is None:
                            raise RuntimeError("Sticky cog unavailable")
                        await cog.post_sticky(str(decoded(task["payload_json"], {})["channel_id"]), force=True)
                    elif task["type"] == "resend_all_stickies":
                        cog = bot.get_cog("Sticky")
                        if cog is None:
                            raise RuntimeError("Sticky cog unavailable")
                        rows = all_rows("SELECT channel_id FROM sticky_channels WHERE guild_id = ? AND enabled = 1",
                                        (str(GUILD_ID),))
                        for row in rows:
                            await cog.post_sticky(row["channel_id"], force=True)
                    elif task["type"] == "post_stats":
                        cog = bot.get_cog("Stats")
                        if cog is None:
                            raise RuntimeError("Stats cog unavailable")
                        await cog.post_stats(force=True)
                    elif task["type"] == "post_rules":
                        cog = bot.get_cog("Verification")
                        if cog is None:
                            raise RuntimeError("Verification cog unavailable")
                        await cog.post_rules(resend=bool(decoded(task["payload_json"], {}).get("resend")))
                    elif task["type"] == "db_maintenance":
                        await asyncio.to_thread(run_maintenance)
                    else:
                        raise ValueError("Unknown task type")
                except Exception as exc:
                    error = str(exc)[:1000]
                    log.exception("Bot task %s failed", task["id"])
                with connect() as db:
                    db.execute("UPDATE bot_tasks SET status = ?, processed_at = ?, error = ? WHERE id = ?",
                               ("failed" if error else "done", datetime.now(timezone.utc).isoformat(), error, task["id"]))
        except Exception:
            log.exception("Task poll failed")
        await asyncio.sleep(2)
