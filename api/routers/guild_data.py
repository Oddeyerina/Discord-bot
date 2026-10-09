import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database import get_db
from models import GuildChannel, GuildEmoji, GuildRole
from routers.common import guild_id

router = APIRouter(prefix="/api/guild", tags=["guild"])
internal_router = APIRouter(prefix="/internal", tags=["internal"])


class GuildSync(BaseModel):
    guild_id: str
    channels: list[dict[str, Any]]
    roles: list[dict[str, Any]]
    emojis: list[dict[str, Any]]


@router.get("/data")
def data(db: Session = Depends(get_db)) -> dict[str, Any]:
    gid = guild_id()
    return {
        "channels": [{"id": row.id, "name": row.name, "type": row.type}
                     for row in db.scalars(select(GuildChannel).where(GuildChannel.guild_id == gid))],
        "roles": [{"id": row.id, "name": row.name, "position": row.position}
                  for row in db.scalars(select(GuildRole).where(GuildRole.guild_id == gid))],
        "emojis": [{"id": row.id, "name": row.name, "animated": row.animated}
                   for row in db.scalars(select(GuildEmoji).where(GuildEmoji.guild_id == gid))],
    }


@internal_router.post("/guild-sync")
def sync(body: GuildSync, x_internal_secret: str = Header(default=""),
         db: Session = Depends(get_db)) -> dict[str, bool]:
    import hmac
    if not hmac.compare_digest(x_internal_secret, os.getenv("SESSION_SECRET", "")) or body.guild_id != guild_id():
        raise HTTPException(status_code=403)
    gid = guild_id()
    for model in (GuildChannel, GuildRole, GuildEmoji):
        db.execute(delete(model).where(model.guild_id == gid))
    db.add_all(GuildChannel(id=str(x["id"]), guild_id=gid, name=x["name"], type=x["type"])
               for x in body.channels)
    db.add_all(GuildRole(id=str(x["id"]), guild_id=gid, name=x["name"], position=x["position"])
               for x in body.roles)
    db.add_all(GuildEmoji(id=str(x["id"]), guild_id=gid, name=x["name"], animated=x["animated"])
               for x in body.emojis)
    db.commit()
    return {"ok": True}
