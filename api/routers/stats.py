import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import StatsConfig
from routers.common import enqueue, guild_id
from schemas import StatsInput


router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(StatsConfig).where(StatsConfig.guild_id == guild_id()))
    if row is None:
        return {}
    return {"channel_id": row.channel_id, "message_id": row.message_id,
            "embed": json.loads(row.embed_json or "{}"),
            "update_interval_seconds": row.update_interval_seconds, "enabled": row.enabled,
            "role_counters": json.loads(row.role_counters_json or "[]"),
            "last_updated": row.last_updated}


@router.put("/config")
def put_config(body: StatsInput, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(StatsConfig).where(StatsConfig.guild_id == guild_id()))
    if row is None:
        row = StatsConfig(guild_id=guild_id())
        db.add(row)
    if row.channel_id != body.channel_id:
        row.message_id = None
    row.channel_id = body.channel_id
    row.embed_json = body.embed.model_dump_json()
    row.update_interval_seconds = body.update_interval_seconds
    row.enabled = body.enabled
    row.role_counters_json = json.dumps([counter.model_dump() for counter in body.role_counters])
    db.commit()
    return get_config(db)


@router.post("/resend")
def resend(db: Session = Depends(get_db)) -> dict[str, int]:
    return {"task_id": enqueue(db, "post_stats", {}).id}
