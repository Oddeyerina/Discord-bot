from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import WelcomeConfig
from routers.common import guild_id
from schemas import WelcomeInput
import json

router = APIRouter(prefix="/api/welcome", tags=["welcome"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(WelcomeConfig).where(WelcomeConfig.guild_id == guild_id()))
    if row is None:
        return {}
    return {"welcome_channel_id": row.welcome_channel_id,
            "welcome_embed": json.loads(row.welcome_embed_json),
            "goodbye_channel_id": row.goodbye_channel_id,
            "goodbye_embed": json.loads(row.goodbye_embed_json),
            "autorole_ids": json.loads(row.autorole_ids_json or "[]")}


@router.put("/config")
def put_config(body: WelcomeInput, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(WelcomeConfig).where(WelcomeConfig.guild_id == guild_id()))
    if row is None:
        row = WelcomeConfig(guild_id=guild_id())
        db.add(row)
    row.welcome_channel_id = body.welcome_channel_id
    row.welcome_embed_json = body.welcome_embed.model_dump_json()
    row.goodbye_channel_id = body.goodbye_channel_id
    row.goodbye_embed_json = body.goodbye_embed.model_dump_json()
    row.autorole_ids_json = json.dumps(body.autorole_ids)
    db.commit()
    return get_config(db)
