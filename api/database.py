import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/dcbot.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def configure_sqlite(connection: object, _: object) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def migrate_ticket_timestamps() -> None:
    """Add Phase 1 ticket timestamps to an existing SQLite database."""
    with engine.begin() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(tickets)")}
        for name in ("answered_at", "pinged_at"):
            if name not in columns:
                connection.exec_driver_sql(f"ALTER TABLE tickets ADD COLUMN {name} DATETIME")


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
