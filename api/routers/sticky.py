import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import StickyChannel
from routers.common import enqueue, guild_id
from schemas import StickyInput

router = APIRouter(prefix="/api/sticky", tags=["sticky"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(StickyChannel).where(StickyChannel.guild_id == guild_id())
                      .order_by(StickyChannel.id)).all()
    return {"channels": [{"channel_id": row.channel_id, "role_id": row.role_id,
                          "sticky_embed": json.loads(row.sticky_embed_json), "enabled": row.enabled,
                          "cooldown_seconds": row.cooldown_seconds} for row in rows]}


@router.put("/config")
def put_config(body: dict[str, list[StickyInput]], db: Session = Depends(get_db)) -> dict:
    inputs = body.get("channels", [])
    ids = [item.channel_id for item in inputs]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Sticky channels must be unique")
    existing = {row.channel_id: row for row in db.scalars(
        select(StickyChannel).where(StickyChannel.guild_id == guild_id()))}
    for channel_id, row in existing.items():
        if channel_id not in ids:
            db.delete(row)
    for item in inputs:
        row = existing.get(item.channel_id)
        if row is None:
            row = StickyChannel(guild_id=guild_id(), channel_id=item.channel_id)
            db.add(row)
        row.role_id = item.role_id or None
        row.sticky_embed_json = item.sticky_embed.model_dump_json()
        row.cooldown_seconds = item.cooldown_seconds
        row.enabled = item.enabled
    db.commit()
    return get_config(db)


@router.post("/post/{channel_id}")
def post_now(channel_id: str, db: Session = Depends(get_db)) -> dict[str, int]:
    row = db.scalar(select(StickyChannel).where(StickyChannel.guild_id == guild_id(),
                                                 StickyChannel.channel_id == channel_id))
    if row is None:
        raise HTTPException(404, "Sticky channel not configured")
    return {"task_id": enqueue(db, "post_sticky", {"channel_id": channel_id}).id}
