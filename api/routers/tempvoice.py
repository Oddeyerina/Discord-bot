from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import TempVoiceActive, TempVoiceConfig
from routers.common import guild_id
from schemas import TempVoiceInput

router = APIRouter(prefix="/api/tempvoice", tags=["tempvoice"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(TempVoiceConfig).where(TempVoiceConfig.guild_id == guild_id()))
    return {} if row is None else {key: getattr(row, key) for key in
        ("hub_channel_id", "category_id", "name_template", "user_limit", "enabled")}


@router.put("/config")
def put_config(body: TempVoiceInput, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(TempVoiceConfig).where(TempVoiceConfig.guild_id == guild_id()))
    if row is None:
        row = TempVoiceConfig(guild_id=guild_id())
        db.add(row)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return get_config(db)


@router.get("/active")
def active(db: Session = Depends(get_db)) -> list[dict]:
    return [{"channel_id": row.channel_id, "owner_id": row.owner_id}
            for row in db.scalars(select(TempVoiceActive).where(TempVoiceActive.guild_id == guild_id()))]
