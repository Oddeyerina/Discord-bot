"""Moderation settings and read-only warning history."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import ModerationConfig, WarningRecord
from routers.common import guild_id
from schemas import ModerationInput

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(ModerationConfig).where(ModerationConfig.guild_id == guild_id()))
    if row is None:
        return {}
    return {"warn_kick_threshold": row.warn_kick_threshold,
            "warn_ban_threshold": row.warn_ban_threshold,
            "log_channel_id": row.log_channel_id, "dm_on_warn": row.dm_on_warn}


@router.put("/config")
def put_config(body: ModerationInput, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(ModerationConfig).where(ModerationConfig.guild_id == guild_id()))
    if row is None:
        row = ModerationConfig(guild_id=guild_id())
        db.add(row)
    for field in ("warn_kick_threshold", "warn_ban_threshold", "log_channel_id", "dm_on_warn"):
        setattr(row, field, getattr(body, field))
    db.commit()
    return get_config(db)


@router.get("/warnings")
def warnings(user_id: str = "", db: Session = Depends(get_db)) -> list[dict]:
    query = select(WarningRecord).where(WarningRecord.guild_id == guild_id())
    if user_id:
        query = query.where(WarningRecord.user_id == user_id)
    return [{"id": row.id, "user_id": row.user_id, "moderator_id": row.moderator_id,
             "reason": row.reason, "created_at": row.created_at}
            for row in db.scalars(query.order_by(WarningRecord.id.desc()).limit(100))]
