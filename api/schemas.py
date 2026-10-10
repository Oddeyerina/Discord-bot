from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EmbedData(BaseModel):
    title: str = Field(default="", max_length=256)
    description: str = Field(default="", max_length=4096)
    color: str = "#5865F2"
    footer: str = Field(default="", max_length=2048)
    thumbnail: str = ""
    image: str = ""


class PanelInput(BaseModel):
    channel_id: str
    embed: EmbedData
    extra_config: dict[str, Any] = Field(default_factory=dict)


class ReasonInput(BaseModel):
    id: int | None = None
    label: str = Field(min_length=1, max_length=100)
    emoji: str | None = None
    description: str = ""
    support_role_ids: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class PriorityInput(BaseModel):
    id: int | None = None
    label: str = Field(min_length=1, max_length=100)
    emoji: str | None = None
    color: str = Field(default="#5865F2", pattern=r"^#[0-9a-fA-F]{6}$")


class AutoresponseInput(BaseModel):
    trigger_keyword: str = Field(min_length=1, max_length=100)
    response_text: str = Field(min_length=1, max_length=2000)
    enabled: bool = True


class QuickreplyInput(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    response_text: str = Field(min_length=1, max_length=2000)


class TicketInput(PanelInput):
    reasons: list[ReasonInput] = Field(default_factory=list, max_length=25)
    priorities: list[PriorityInput] = Field(default_factory=list, max_length=25)
    autoresponses: list[AutoresponseInput] = Field(default_factory=list)
    quickreplies: list[QuickreplyInput] = Field(default_factory=list, max_length=25)


class TicketRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: str
    panel_id: int
    user_id: str
    reason_id: int
    priority_id: int | None
    status: str
    claimed_by: str | None
    created_at: datetime
    answered_at: datetime | None
    pinged_at: datetime | None
    closed_at: datetime | None
    transcript_path: str | None


class ReactionMappingInput(BaseModel):
    emoji: str
    role_id: str


class ReactionRoleInput(PanelInput):
    style: Literal["reaction", "select"] = "reaction"
    mappings: list[ReactionMappingInput] = Field(default_factory=list, max_length=25)


class HoneypotInput(BaseModel):
    channel_id: str
    action: Literal["kick", "ban", "timeout"] = "kick"
    timeout_seconds: int = Field(default=3600, ge=1, le=2419200)
    log_channel_id: str | None = None
    delete_message: bool = True
    dm_user: bool = False
    whitelist_role_ids: list[str] = Field(default_factory=list)
    embed: EmbedData = Field(default_factory=EmbedData)


class LevelRoleInput(BaseModel):
    level: int = Field(ge=1)
    role_id: str


class LevelInput(BaseModel):
    xp_per_message: int = Field(default=15, ge=1, le=10000)
    cooldown_seconds: int = Field(default=60, ge=0, le=86400)
    base_xp: int = Field(default=100, ge=1)
    multiplier: float = Field(default=1.5, ge=1.0, le=10.0)
    announcement_channel_id: str | None = None
    ignored_channel_ids: list[str] = Field(default_factory=list)
    ignored_role_ids: list[str] = Field(default_factory=list)
    levelup_embed: EmbedData = Field(default_factory=EmbedData)
    roles: list[LevelRoleInput] = Field(default_factory=list)


class WelcomeInput(BaseModel):
    welcome_channel_id: str | None = None
    welcome_embed: EmbedData = Field(default_factory=EmbedData)
    goodbye_channel_id: str | None = None
    goodbye_embed: EmbedData = Field(default_factory=EmbedData)
    autorole_id: str | None = None


class TaskInput(BaseModel):
    type: Literal["post_panel", "update_panel", "sync_guild_data", "post_sticky"]
    payload: dict[str, Any] = Field(default_factory=dict)


class StickyInput(BaseModel):
    channel_id: str
    role_id: str | None = None
    sticky_embed: EmbedData = Field(default_factory=EmbedData)
    cooldown_seconds: int = Field(default=60, ge=0, le=86400)
    enabled: bool = True


class TempVoiceInput(BaseModel):
    hub_channel_id: str | None = None
    category_id: str | None = None
    name_template: str = Field(default="🔊 {user}'s channel", min_length=1, max_length=100)
    user_limit: int = Field(default=0, ge=0, le=99)
    enabled: bool = False


class StickyRolesInput(BaseModel):
    excluded_role_ids: list[str] = Field(default_factory=list)
    enabled: bool = False


class RememberingInput(BaseModel):
    channel_id: str | None = None
    announcement_embed: EmbedData = Field(default_factory=EmbedData)
    timezone: str = "Europe/Berlin"
    enabled: bool = False
