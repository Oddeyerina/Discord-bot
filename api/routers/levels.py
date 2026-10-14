import json

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database import get_db
from models import LevelConfig, LevelRole, LevelUser
from routers.common import guild_id
from schemas import LevelInput

router = APIRouter(prefix="/api/levels", tags=["levels"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(LevelConfig).where(LevelConfig.guild_id == guild_id()))
    if row is None:
        return {}
    return {"xp_per_message": row.xp_per_message, "cooldown_seconds": row.cooldown_seconds,
            "base_xp": row.base_xp, "multiplier": row.multiplier,
            "voice_xp_per_minute": row.voice_xp_per_minute,
            "voice_ignored_channel_ids": json.loads(row.voice_ignored_channel_ids_json),
            "announcement_channel_id": row.announcement_channel_id,
            "ignored_channel_ids": json.loads(row.ignored_channel_ids_json),
            "ignored_role_ids": json.loads(row.ignored_role_ids_json),
            "levelup_embed": json.loads(row.levelup_embed_json),
            "roles": [{"level": r.level, "role_id": r.role_id} for r in
                      db.scalars(select(LevelRole).where(LevelRole.guild_id == guild_id()))]}


@router.put("/config")
def put_config(body: LevelInput, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(LevelConfig).where(LevelConfig.guild_id == guild_id()))
    if row is None:
        row = LevelConfig(guild_id=guild_id())
        db.add(row)
    for field in ("xp_per_message", "cooldown_seconds", "base_xp", "multiplier", "announcement_channel_id", "voice_xp_per_minute"):
        setattr(row, field, getattr(body, field))
    row.ignored_channel_ids_json = json.dumps(body.ignored_channel_ids)
    row.ignored_role_ids_json = json.dumps(body.ignored_role_ids)
    row.voice_ignored_channel_ids_json = json.dumps(body.voice_ignored_channel_ids)
    row.levelup_embed_json = body.levelup_embed.model_dump_json()
    db.execute(delete(LevelRole).where(LevelRole.guild_id == guild_id()))
    db.add_all(LevelRole(guild_id=guild_id(), level=r.level, role_id=r.role_id) for r in body.roles)
    db.commit()
    return get_config(db)


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)) -> list[dict]:
    return [{"user_id": r.user_id, "xp": r.xp, "level": r.level,
             "messages_count": r.messages_count} for r in
            db.scalars(select(LevelUser).where(LevelUser.guild_id == guild_id())
                       .order_by(LevelUser.xp.desc()).limit(25))]
