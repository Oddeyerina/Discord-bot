"""Rules verification configuration and publish tasks."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import VerificationConfig
from routers.common import enqueue, guild_id
from schemas import VerificationInput

router = APIRouter(prefix="/api/verification", tags=["verification"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(VerificationConfig).where(VerificationConfig.guild_id == guild_id()))
    if row is None:
        return {}
    return {"rules_channel_id": row.rules_channel_id, "rules_message_id": row.rules_message_id,
            "rules_embed": json.loads(row.rules_embed_json or "{}"),
            "button_label": row.button_label, "verified_role_id": row.verified_role_id,
            "enabled": row.enabled}


@router.put("/config")
def put_config(body: VerificationInput, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(VerificationConfig).where(VerificationConfig.guild_id == guild_id()))
    if row is None:
        row = VerificationConfig(guild_id=guild_id())
        db.add(row)
    if row.rules_channel_id != body.rules_channel_id:
        row.rules_message_id = None
    row.rules_channel_id = body.rules_channel_id
    row.rules_embed_json = body.rules_embed.model_dump_json()
    row.button_label = body.button_label
    row.verified_role_id = body.verified_role_id
    row.enabled = body.enabled
    db.commit()
    return get_config(db)


@router.post("/post")
def post_rules(resend: bool = False, db: Session = Depends(get_db)) -> dict[str, int]:
    row = db.scalar(select(VerificationConfig).where(VerificationConfig.guild_id == guild_id()))
    if row is None or not row.enabled or not row.rules_channel_id:
        raise HTTPException(400, "Configure and enable rules verification first")
    return {"task_id": enqueue(db, "post_rules", {"resend": resend}).id}
