"""Read-only dashboard audit history."""

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import AuditLog
from routers.common import guild_id

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit(action: str = "", actor: str = "", db: Session = Depends(get_db)) -> list[dict]:
    query = select(AuditLog).where(AuditLog.guild_id == guild_id())
    if action:
        query = query.where(AuditLog.action.startswith(action))
    if actor:
        query = query.where(AuditLog.actor_id == actor)
    rows = db.scalars(query.order_by(AuditLog.id.desc()).limit(200)).all()
    return [{"id": row.id, "actor_id": row.actor_id, "action": row.action,
             "target": row.target, "details": json.loads(row.details_json or "{}"),
             "created_at": row.created_at} for row in rows]
