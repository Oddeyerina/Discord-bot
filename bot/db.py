import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from config import DATABASE_URL, GUILD_ID

DB_PATH = DATABASE_URL.removeprefix("sqlite:///")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(DB_PATH, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def one(sql: str, args: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as db:
        row = db.execute(sql, args).fetchone()
        return dict(row) if row else None


def all_rows(sql: str, args: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as db:
        return [dict(row) for row in db.execute(sql, args).fetchall()]


def settings(table: str) -> dict[str, Any] | None:
    if table not in {"honeypot_config", "level_config", "welcome_config", "tempvoice_config",
                     "sticky_roles_config", "remembered_dates_config", "stats_config"}:
        raise ValueError("Unknown settings table")
    return one(f"SELECT * FROM {table} WHERE guild_id = ?", (str(GUILD_ID),))


def panel(kind: str) -> dict[str, Any] | None:
    return one("SELECT * FROM panels WHERE guild_id = ? AND type = ?", (str(GUILD_ID), kind))


def decoded(value: str | None, fallback: Any = None) -> Any:
    return json.loads(value) if value else fallback
