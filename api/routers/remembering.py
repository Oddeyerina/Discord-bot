import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import RememberedDate, RememberedDatesConfig
from routers.common import guild_id
from schemas import RememberingInput

router = APIRouter(prefix="/api/remembering", tags=["remembering"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(RememberedDatesConfig).where(RememberedDatesConfig.guild_id == guild_id()))
    if row is None:
        return {}
    return {"channel_id": row.channel_id, "announcement_embed": json.loads(row.announcement_embed_json),
            "label_embeds": json.loads(row.label_embed_json or "{}"),
            "timezone": row.timezone, "enabled": row.enabled}


@router.put("/config")
def put_config(body: RememberingInput, db: Session = Depends(get_db)) -> dict:
    try:
        ZoneInfo(body.timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(422, "Unknown timezone") from exc
    row = db.scalar(select(RememberedDatesConfig).where(RememberedDatesConfig.guild_id == guild_id()))
    if row is None:
        row = RememberedDatesConfig(guild_id=guild_id())
        db.add(row)
    row.channel_id = body.channel_id or None
    row.announcement_embed_json = body.announcement_embed.model_dump_json()
    row.label_embed_json = json.dumps({label: embed.model_dump() for label, embed in body.label_embeds.items()})
    row.timezone = body.timezone
    row.enabled = body.enabled
    db.commit()
    return get_config(db)


@router.get("/dates")
def dates(db: Session = Depends(get_db)) -> list[dict]:
    return [{"user_id": row.user_id, "date_day": row.date_day, "date_month": row.date_month,
             "date_year": row.date_year, "label": row.label}
            for row in db.scalars(select(RememberedDate).where(RememberedDate.guild_id == guild_id())
                                  .order_by(RememberedDate.date_month, RememberedDate.date_day))]
