import json

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database import get_db
from models import ReactionRole
from routers.common import guild_id, panel_data, panel_for, save_panel
from schemas import ReactionRoleInput

router = APIRouter(prefix="/api/reaction-roles", tags=["reaction roles"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    panel = panel_for(db, "reactionroles")
    result = panel_data(panel)
    result["mappings"] = [] if panel is None else [
        {"emoji": row.emoji, "role_id": row.role_id} for row in
        db.scalars(select(ReactionRole).where(ReactionRole.panel_id == panel.id)
                   .order_by(ReactionRole.position))]
    result["style"] = "reaction" if panel is None else json.loads(panel.extra_config_json).get("style", "reaction")
    return result


@router.put("/config")
def put_config(body: ReactionRoleInput, db: Session = Depends(get_db)) -> dict:
    panel = save_panel(db, "reactionroles", body.channel_id, body.embed, {"style": body.style})
    db.execute(delete(ReactionRole).where(ReactionRole.panel_id == panel.id))
    for pos, mapping in enumerate(body.mappings):
        db.add(ReactionRole(guild_id=guild_id(), panel_id=panel.id,
                            emoji=mapping.emoji, role_id=mapping.role_id, position=pos))
    db.commit()
    return get_config(db)
