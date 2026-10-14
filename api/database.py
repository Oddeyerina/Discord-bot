import os
import json
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def configure_sqlite(connection: object, _: object) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def migrate_ticket_columns() -> None:
    """Add ticket columns to existing SQLite databases without discarding rows."""
    with engine.begin() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(tickets)")}
        for name in ("answered_at", "pinged_at"):
            if name not in columns:
                connection.exec_driver_sql(f"ALTER TABLE tickets ADD COLUMN {name} DATETIME")
        if "priority_id" not in columns:
            connection.exec_driver_sql("ALTER TABLE tickets ADD COLUMN priority_id INTEGER REFERENCES ticket_priorities(id)")


def migrate_phase_b() -> None:
    """Keep existing configuration while adding multi-panel and Phase B columns."""
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")

        def columns(table: str) -> set[str]:
            return {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}

        indexes = cursor.execute("PRAGMA index_list(panels)").fetchall()
        unique_panel = any(row[2] and [part[2] for part in cursor.execute(
            f"PRAGMA index_info('{row[1]}')").fetchall()] == ["guild_id", "type"] for row in indexes)
        if unique_panel:
            cursor.execute("CREATE TABLE panels_phase_b (id INTEGER PRIMARY KEY, guild_id VARCHAR NOT NULL, "
                           "type VARCHAR NOT NULL, name VARCHAR, active BOOLEAN DEFAULT 1, "
                           "channel_id VARCHAR NOT NULL, message_id VARCHAR, embed_json TEXT, extra_config_json TEXT)")
            cursor.execute("INSERT INTO panels_phase_b (id, guild_id, type, name, active, channel_id, "
                           "message_id, embed_json, extra_config_json) SELECT id, guild_id, type, NULL, 1, "
                           "channel_id, message_id, embed_json, extra_config_json FROM panels")
            cursor.execute("DROP TABLE panels")
            cursor.execute("ALTER TABLE panels_phase_b RENAME TO panels")
            cursor.execute("CREATE INDEX ix_panels_guild_id ON panels (guild_id)")
        else:
            if "name" not in columns("panels"):
                cursor.execute("ALTER TABLE panels ADD COLUMN name VARCHAR")
            if "active" not in columns("panels"):
                cursor.execute("ALTER TABLE panels ADD COLUMN active BOOLEAN DEFAULT 1")

        for table in ("ticket_priorities", "ticket_quickreplies"):
            if "panel_id" not in columns(table):
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN panel_id INTEGER REFERENCES panels(id)")
            cursor.execute(f"UPDATE {table} SET panel_id = (SELECT MIN(id) FROM panels "
                           f"WHERE panels.guild_id = {table}.guild_id AND panels.type = 'tickets') "
                           "WHERE panel_id IS NULL")
        if "control_channel_id" not in columns("tempvoice_config"):
            cursor.execute("ALTER TABLE tempvoice_config ADD COLUMN control_channel_id VARCHAR")
        if "autorole_ids_json" not in columns("welcome_config"):
            cursor.execute("ALTER TABLE welcome_config ADD COLUMN autorole_ids_json TEXT DEFAULT '[]'")
            if "autorole_id" in columns("welcome_config"):
                for row_id, role_id in cursor.execute(
                    "SELECT id, autorole_id FROM welcome_config WHERE autorole_id IS NOT NULL").fetchall():
                    cursor.execute("UPDATE welcome_config SET autorole_ids_json = ? WHERE id = ?",
                                   (json.dumps([role_id]), row_id))
        if "label_embed_json" not in columns("remembered_dates_config"):
            cursor.execute("ALTER TABLE remembered_dates_config ADD COLUMN label_embed_json TEXT DEFAULT '{}'")
        raw.commit()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    finally:
        raw.close()


def migrate_phase_c() -> None:
    """Add Phase C columns to existing SQLite tables without dropping data."""
    columns = {
        "tickets": {"assigned_to": "VARCHAR", "last_warned_at": "DATETIME"},
        "level_config": {
            "voice_xp_per_minute": "INTEGER NOT NULL DEFAULT 5",
            "voice_ignored_channel_ids_json": "TEXT NOT NULL DEFAULT '[]'",
        },
        "level_users": {
            "voice_seconds_last_grant": "DATETIME",
            "messages_count": "INTEGER NOT NULL DEFAULT 0",
        },
    }
    with engine.begin() as connection:
        for table, additions in columns.items():
            existing = {row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")}
            for name, definition in additions.items():
                if name not in existing:
                    connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
