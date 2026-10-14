import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Panel, ReactionRole
from routers.common import enqueue, guild_id, panel_data, panel_for, panel_for_id
from schemas import ReactionRoleInput


router = APIRouter(prefix="/api/reaction-roles", tags=["reaction roles"])


def config_data(db: Session, panel: Panel) -> dict:
    result = panel_data(panel)
    result["mappings"] = [
        {"emoji": row.emoji, "role_id": row.role_id}
        for row in db.scalars(select(ReactionRole).where(ReactionRole.panel_id == panel.id)
                              .order_by(ReactionRole.position))]
    result["style"] = json.loads(panel.extra_config_json or "{}").get("style", "reaction")
    return result


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> list[dict]:
    panels = db.scalars(select(Panel).where(Panel.guild_id == guild_id(), Panel.type == "reactionroles",
                                             Panel.active.is_(True)).order_by(Panel.id)).all()
    return [config_data(db, panel) for panel in panels]


@router.get("/config/{panel_id}")
def get_one(panel_id: int, db: Session = Depends(get_db)) -> dict:
    panel = panel_for_id(db, "reactionroles", panel_id)
    if panel is None:
        raise HTTPException(404, "Reaction role panel not found")
    return config_data(db, panel)


def save_config(db: Session, panel: Panel, body: ReactionRoleInput) -> dict:
    panel.name = body.name or None
    panel.channel_id = body.channel_id
    panel.embed_json = body.embed.model_dump_json()
    panel.extra_config_json = json.dumps({"style": body.style})
    db.flush()
    for row in db.scalars(select(ReactionRole).where(ReactionRole.panel_id == panel.id)):
        db.delete(row)
    db.flush()
    for position, mapping in enumerate(body.mappings):
        db.add(ReactionRole(guild_id=guild_id(), panel_id=panel.id,
                            emoji=mapping.emoji, role_id=mapping.role_id, position=position))
    db.commit()
    return config_data(db, panel)


@router.post("/config")
def create_config(body: ReactionRoleInput, db: Session = Depends(get_db)) -> dict:
    panel = Panel(guild_id=guild_id(), type="reactionroles", channel_id=body.channel_id, active=True)
    db.add(panel)
    return save_config(db, panel, body)


@router.put("/config/{panel_id}")
def update_config(panel_id: int, body: ReactionRoleInput, db: Session = Depends(get_db)) -> dict:
    panel = panel_for_id(db, "reactionroles", panel_id)
    if panel is None:
        raise HTTPException(404, "Reaction role panel not found")
    return save_config(db, panel, body)


@router.put("/config")
def put_legacy_config(body: ReactionRoleInput, db: Session = Depends(get_db)) -> dict:
    panel = panel_for(db, "reactionroles")
    if panel is None:
        panel = Panel(guild_id=guild_id(), type="reactionroles", channel_id=body.channel_id, active=True)
        db.add(panel)
    return save_config(db, panel, body)


@router.delete("/config/{panel_id}")
def delete_config(panel_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    panel = panel_for_id(db, "reactionroles", panel_id)
    if panel is None:
        raise HTTPException(404, "Reaction role panel not found")
    panel.active = False
    db.commit()
    return {"task_id": enqueue(db, "delete_panel", {"panel_id": panel.id}).id}
