import json
import os
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import BotTask, Panel


def guild_id() -> str:
    value = os.getenv("DISCORD_GUILD_ID", "")
    if not value:
        raise HTTPException(status_code=503, detail="DISCORD_GUILD_ID is not set")
    return value


def panel_for(db: Session, kind: str) -> Panel | None:
    return db.scalar(select(Panel).where(Panel.guild_id == guild_id(), Panel.type == kind))


def save_panel(db: Session, kind: str, channel_id: str, embed: Any,
               extra: dict[str, Any]) -> Panel:
    panel = panel_for(db, kind)
    if panel is None:
        panel = Panel(guild_id=guild_id(), type=kind, channel_id=channel_id)
        db.add(panel)
    panel.channel_id = channel_id
    panel.embed_json = json.dumps(embed.model_dump() if hasattr(embed, "model_dump") else embed)
    panel.extra_config_json = json.dumps(extra)
    db.flush()
    return panel


def panel_data(panel: Panel | None) -> dict[str, Any]:
    if panel is None:
        return {}
    return {"id": panel.id, "channel_id": panel.channel_id,
            "message_id": panel.message_id, "embed": json.loads(panel.embed_json),
            "extra_config": json.loads(panel.extra_config_json)}


def enqueue(db: Session, kind: str, payload: dict[str, Any]) -> BotTask:
    task = BotTask(guild_id=guild_id(), type=kind, payload_json=json.dumps(payload))
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
