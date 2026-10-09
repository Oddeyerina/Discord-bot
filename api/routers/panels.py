from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from routers.common import enqueue, panel_data, panel_for

router = APIRouter(prefix="/api/panels", tags=["panels"])


@router.get("")
def list_panels(db: Session = Depends(get_db)) -> list[dict]:
    return [panel_data(panel_for(db, kind)) for kind in ("tickets", "honeypot", "reactionroles")]


@router.post("/{kind}/publish")
def publish(kind: str, db: Session = Depends(get_db)) -> dict[str, int]:
    if kind not in ("tickets", "honeypot", "reactionroles"):
        raise HTTPException(status_code=404)
    panel = panel_for(db, kind)
    if panel is None:
        raise HTTPException(status_code=400, detail="Save the panel first")
    task = enqueue(db, "update_panel" if panel.message_id else "post_panel", {"panel_id": panel.id})
    return {"task_id": task.id}
