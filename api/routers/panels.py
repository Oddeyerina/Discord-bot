from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Panel
from routers.common import enqueue, guild_id, panel_data, panel_for, panel_for_id

router = APIRouter(prefix="/api/panels", tags=["panels"])


@router.get("")
def list_panels(db: Session = Depends(get_db)) -> list[dict]:
    return [panel_data(panel) for panel in db.scalars(select(Panel).where(
        Panel.guild_id == guild_id(), Panel.active.is_(True)).order_by(Panel.id))]


@router.post("/{kind}/publish")
def publish(kind: str, db: Session = Depends(get_db)) -> dict[str, int]:
    if kind not in ("tickets", "honeypot", "reactionroles"):
        raise HTTPException(status_code=404)
    panel = panel_for(db, kind)
    if panel is None:
        raise HTTPException(status_code=400, detail="Save the panel first")
    task = enqueue(db, "update_panel" if panel.message_id else "post_panel", {"panel_id": panel.id})
    return {"task_id": task.id}


@router.post("/{kind}/{panel_id}/publish")
def publish_one(kind: str, panel_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    if kind not in ("tickets", "reactionroles"):
        raise HTTPException(404, "Panel type unavailable")
    panel = panel_for_id(db, kind, panel_id)
    if panel is None:
        raise HTTPException(404, "Panel not found")
    task = enqueue(db, "update_panel" if panel.message_id else "post_panel", {"panel_id": panel.id})
    return {"task_id": task.id}
