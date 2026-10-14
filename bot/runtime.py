"""Startup recovery, heartbeat, and scheduled database maintenance."""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import discord

from config import GUILD_ID
from db import DB_PATH, all_rows, connect, one, write_bot_heartbeat

log = logging.getLogger(__name__)


def prepare_runtime() -> None:
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS app_meta (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("UPDATE bot_tasks SET status = 'pending' WHERE status = 'running'")


def recover_guild_state(guild: discord.Guild) -> None:
    with connect() as db:
        for row in db.execute("SELECT id, channel_id FROM tempvoice_active WHERE guild_id = ?",
                              (str(GUILD_ID),)).fetchall():
            if guild.get_channel(int(row["channel_id"])) is None:
                db.execute("DELETE FROM tempvoice_active WHERE id = ?", (row["id"],))
        for row in db.execute("SELECT id, channel_id FROM panels WHERE guild_id = ? AND active = 1",
                              (str(GUILD_ID),)).fetchall():
            if guild.get_channel(int(row["channel_id"])) is not None:
                continue
            panel_id = row["id"]
            if db.execute("SELECT 1 FROM tickets WHERE panel_id = ? LIMIT 1", (panel_id,)).fetchone():
                db.execute("UPDATE panels SET active = 0 WHERE id = ?", (panel_id,))
                continue
            for table in ("reaction_roles", "ticket_reasons", "ticket_priorities",
                          "ticket_autoresponses", "ticket_quickreplies"):
                db.execute(f"DELETE FROM {table} WHERE panel_id = ?", (panel_id,))
            db.execute("DELETE FROM panels WHERE id = ?", (panel_id,))


def run_maintenance() -> None:
    now = datetime.now(timezone.utc)
    db = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    try:
        db.execute("PRAGMA busy_timeout=30000")
        done = db.execute("DELETE FROM bot_tasks WHERE status = 'done' AND processed_at < ?",
                          ((now - timedelta(days=7)).isoformat(),)).rowcount
        failed = db.execute("DELETE FROM bot_tasks WHERE status = 'failed' AND processed_at < ?",
                            ((now - timedelta(days=30)).isoformat(),)).rowcount
        db.execute("VACUUM")
        db.execute("INSERT INTO app_meta (id, value) VALUES ('last_maintenance_at', ?) "
                   "ON CONFLICT(id) DO UPDATE SET value = excluded.value", (now.isoformat(),))
        log.info("DB maintenance removed %s done and %s failed tasks; size %s bytes",
                 done, failed, os.path.getsize(DB_PATH))
    finally:
        db.close()


async def heartbeat_loop(bot: discord.Client) -> None:
    while not bot.is_closed():
        try:
            now = datetime.now(timezone.utc)
            guild = bot.get_guild(GUILD_ID)
            if guild is None:
                online = in_voice = total = None
            else:
                online = sum(1 for member in guild.members if not member.bot and
                             member.status != discord.Status.offline)
                in_voice = sum(1 for member in guild.members if not member.bot and
                               member.voice is not None and member.voice.channel is not None)
                total = guild.member_count or len(guild.members)
            await asyncio.to_thread(write_bot_heartbeat, now.isoformat(), online, in_voice, total)
            last = one("SELECT value FROM app_meta WHERE id = 'last_maintenance_at'")
            due = not last or now - datetime.fromisoformat(last["value"]).replace(
                tzinfo=timezone.utc) >= timedelta(hours=24)
            if due:
                pending = all_rows("SELECT id FROM bot_tasks WHERE type = 'db_maintenance' "
                                   "AND status IN ('pending', 'running') LIMIT 1")
                if not pending:
                    with connect() as db:
                        db.execute("INSERT INTO bot_tasks (guild_id, type, payload_json, status, created_at) "
                                   "VALUES (?, 'db_maintenance', '{}', 'pending', ?)",
                                   (str(GUILD_ID), now.isoformat()))
        except Exception:
            log.exception("Heartbeat or maintenance scheduling failed")
        await asyncio.sleep(30)
