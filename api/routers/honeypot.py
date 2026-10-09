import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import HoneypotConfig
from routers.common import guild_id, panel_data, panel_for, save_panel
from schemas import HoneypotInput

router = APIRouter(prefix="/api/honeypot", tags=["honeypot"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(HoneypotConfig).where(HoneypotConfig.guild_id == guild_id()))
    return {**panel_data(panel_for(db, "honeypot")), **({} if row is None else {
        "channel_id": row.channel_id, "action": row.action, "timeout_seconds": row.timeout_seconds,
        "log_channel_id": row.log_channel_id, "delete_message": row.delete_message,
        "dm_user": row.dm_user, "whitelist_role_ids": json.loads(row.whitelist_role_ids_json)})}


@router.put("/config")
def put_config(body: HoneypotInput, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(HoneypotConfig).where(HoneypotConfig.guild_id == guild_id()))
    if row is None:
        row = HoneypotConfig(guild_id=guild_id())
        db.add(row)
    row.channel_id = body.channel_id
    row.action = body.action
    row.timeout_seconds = body.timeout_seconds
    row.log_channel_id = body.log_channel_id
    row.delete_message = body.delete_message
    row.dm_user = body.dm_user
    row.whitelist_role_ids_json = json.dumps(body.whitelist_role_ids)
    save_panel(db, "honeypot", body.channel_id, body.embed, {})
    db.commit()
    return get_config(db)
