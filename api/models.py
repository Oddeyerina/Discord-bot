from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


# SQLite stores no timezone offset, so timestamps are treated as UTC on read.
def now() -> datetime:
    return datetime.now(timezone.utc)


class GuildChannel(Base):
    __tablename__ = "guild_channels"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)


class GuildRole(Base):
    __tablename__ = "guild_roles"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer, default=0)


class GuildEmoji(Base):
    __tablename__ = "guild_emojis"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    animated: Mapped[bool] = mapped_column(Boolean, default=False)


class Panel(Base):
    __tablename__ = "panels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)
    channel_id: Mapped[str] = mapped_column(String)
    message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    embed_json: Mapped[str] = mapped_column(Text, default="{}")
    extra_config_json: Mapped[str] = mapped_column(Text, default="{}")
    __table_args__ = (UniqueConstraint("guild_id", "type"),)


class TicketReason(Base):
    __tablename__ = "ticket_reasons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("panels.id"))
    label: Mapped[str] = mapped_column(String)
    emoji: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, default="")
    support_role_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    questions_json: Mapped[str] = mapped_column(Text, default="[]")
    position: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    thread_id: Mapped[str] = mapped_column(String, unique=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("panels.id"))
    user_id: Mapped[str] = mapped_column(String)
    reason_id: Mapped[int] = mapped_column(ForeignKey("ticket_reasons.id"))
    status: Mapped[str] = mapped_column(String, default="open")
    claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    pinged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transcript_path: Mapped[str | None] = mapped_column(String, nullable=True)


class HoneypotConfig(Base):
    __tablename__ = "honeypot_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, default="kick")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    log_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    delete_message: Mapped[bool] = mapped_column(Boolean, default=True)
    dm_user: Mapped[bool] = mapped_column(Boolean, default=False)
    whitelist_role_ids_json: Mapped[str] = mapped_column(Text, default="[]")


class ReactionRole(Base):
    __tablename__ = "reaction_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("panels.id"))
    emoji: Mapped[str] = mapped_column(String)
    role_id: Mapped[str] = mapped_column(String)
    position: Mapped[int] = mapped_column(Integer, default=0)


class LevelConfig(Base):
    __tablename__ = "level_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    xp_per_message: Mapped[int] = mapped_column(Integer, default=15)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60)
    base_xp: Mapped[int] = mapped_column(Integer, default=100)
    multiplier: Mapped[float] = mapped_column(Float, default=1.5)
    announcement_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    ignored_channel_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    ignored_role_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    levelup_embed_json: Mapped[str] = mapped_column(Text, default="{}")


class LevelRole(Base):
    __tablename__ = "level_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    level: Mapped[int] = mapped_column(Integer)
    role_id: Mapped[str] = mapped_column(String)


class LevelUser(Base):
    __tablename__ = "level_users"
    guild_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=0)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    last_xp_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WelcomeConfig(Base):
    __tablename__ = "welcome_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    welcome_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    welcome_embed_json: Mapped[str] = mapped_column(Text, default="{}")
    goodbye_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    goodbye_embed_json: Mapped[str] = mapped_column(Text, default="{}")
    autorole_id: Mapped[str | None] = mapped_column(String, nullable=True)


class BotTask(Base):
    __tablename__ = "bot_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    type: Mapped[str] = mapped_column(String)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String, default="pending")
    # SQLite stores no timezone offset; treat this value as UTC on read.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
