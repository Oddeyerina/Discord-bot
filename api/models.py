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
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    channel_id: Mapped[str] = mapped_column(String)
    message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    embed_json: Mapped[str] = mapped_column(Text, default="{}")
    extra_config_json: Mapped[str] = mapped_column(Text, default="{}")


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


class TicketPriority(Base):
    __tablename__ = "ticket_priorities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    panel_id: Mapped[int | None] = mapped_column(ForeignKey("panels.id"), nullable=True)
    label: Mapped[str] = mapped_column(String)
    emoji: Mapped[str | None] = mapped_column(String, nullable=True)
    color: Mapped[str] = mapped_column(String, default="#5865F2")
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
    priority_id: Mapped[int | None] = mapped_column(ForeignKey("ticket_priorities.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="open")
    claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String, nullable=True)
    last_warned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    pinged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SQLite stores no timezone offset; treat this value as UTC on read.
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transcript_path: Mapped[str | None] = mapped_column(String, nullable=True)


class TicketNote(Base):
    __tablename__ = "ticket_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    author_id: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TicketAutoresponse(Base):
    __tablename__ = "ticket_autoresponses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    panel_id: Mapped[int | None] = mapped_column(ForeignKey("panels.id"), nullable=True)
    trigger_keyword: Mapped[str] = mapped_column(String)
    response_text: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class TicketQuickreply(Base):
    __tablename__ = "ticket_quickreplies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    panel_id: Mapped[int | None] = mapped_column(ForeignKey("panels.id"), nullable=True)
    label: Mapped[str] = mapped_column(String)
    response_text: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)


class TicketFirstReply(Base):
    __tablename__ = "ticket_first_replies"
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    message_id: Mapped[str] = mapped_column(String)


class StickyChannel(Base):
    __tablename__ = "sticky_channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    channel_id: Mapped[str] = mapped_column(String)
    role_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sticky_embed_json: Mapped[str] = mapped_column(Text, default="{}")
    sticky_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_sticky_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60)
    __table_args__ = (UniqueConstraint("guild_id", "channel_id"),)


class TempVoiceConfig(Base):
    __tablename__ = "tempvoice_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    hub_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    category_id: Mapped[str | None] = mapped_column(String, nullable=True)
    control_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    name_template: Mapped[str] = mapped_column(String, default="🔊 {user}'s channel")
    user_limit: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class TempVoiceActive(Base):
    __tablename__ = "tempvoice_active"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    channel_id: Mapped[str] = mapped_column(String, unique=True)
    owner_id: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class StickyRolesConfig(Base):
    __tablename__ = "sticky_roles_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    excluded_role_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class StickyRolesSaved(Base):
    __tablename__ = "sticky_roles_saved"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    role_ids_json: Mapped[str] = mapped_column(Text)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("guild_id", "user_id"),)


class RememberedDatesConfig(Base):
    __tablename__ = "remembered_dates_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    announcement_embed_json: Mapped[str] = mapped_column(Text, default="{}")
    label_embed_json: Mapped[str] = mapped_column(Text, default="{}")
    timezone: Mapped[str] = mapped_column(String, default="Europe/Berlin")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class RememberedDate(Base):
    __tablename__ = "remembered_dates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    date_month: Mapped[int] = mapped_column(Integer)
    date_day: Mapped[int] = mapped_column(Integer)
    date_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label: Mapped[str] = mapped_column(String)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("guild_id", "user_id", "label"),)


class RememberedAnnouncement(Base):
    __tablename__ = "remembered_announcements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    date_id: Mapped[int] = mapped_column(ForeignKey("remembered_dates.id"))
    local_date: Mapped[str] = mapped_column(String)
    __table_args__ = (UniqueConstraint("date_id", "local_date"),)


class ScheduledEventRecord(Base):
    __tablename__ = "scheduled_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    discord_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


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
    voice_xp_per_minute: Mapped[int] = mapped_column(Integer, default=5)
    voice_ignored_channel_ids_json: Mapped[str] = mapped_column(Text, default="[]")


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
    voice_seconds_last_grant: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    messages_count: Mapped[int] = mapped_column(Integer, default=0)


class WelcomeConfig(Base):
    __tablename__ = "welcome_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    welcome_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    welcome_embed_json: Mapped[str] = mapped_column(Text, default="{}")
    goodbye_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    goodbye_embed_json: Mapped[str] = mapped_column(Text, default="{}")
    autorole_ids_json: Mapped[str] = mapped_column(Text, default="[]")


class StatsConfig(Base):
    __tablename__ = "stats_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    embed_json: Mapped[str] = mapped_column(Text, default="{}")
    update_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    role_counters_json: Mapped[str] = mapped_column(Text, default="[]")
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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


class AppMeta(Base):
    __tablename__ = "app_meta"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    actor_id: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String, index=True)
    target: Mapped[str] = mapped_column(String)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WarningRecord(Base):
    __tablename__ = "warnings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    moderator_id: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ModerationConfig(Base):
    __tablename__ = "moderation_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    warn_kick_threshold: Mapped[int] = mapped_column(Integer, default=3)
    warn_ban_threshold: Mapped[int] = mapped_column(Integer, default=5)
    log_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    dm_on_warn: Mapped[bool] = mapped_column(Boolean, default=True)


class VerificationConfig(Base):
    __tablename__ = "verification_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True)
    rules_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    rules_message_id: Mapped[str | None] = mapped_column(String, nullable=True)
    rules_embed_json: Mapped[str] = mapped_column(Text, default="{}")
    button_label: Mapped[str] = mapped_column(String, default="I agree to the rules")
    button_custom_id: Mapped[str] = mapped_column(String, default="verify:agree")
    verified_role_id: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
