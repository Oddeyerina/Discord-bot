import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import StickyRolesConfig, StickyRolesSaved
from routers.common import guild_id
from schemas import StickyRolesInput

router = APIRouter(prefix="/api/sticky-roles", tags=["sticky-roles"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(StickyRolesConfig).where(StickyRolesConfig.guild_id == guild_id()))
    return {} if row is None else {"excluded_role_ids": json.loads(row.excluded_role_ids_json),
                                    "enabled": row.enabled}


@router.put("/config")
def put_config(body: StickyRolesInput, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(StickyRolesConfig).where(StickyRolesConfig.guild_id == guild_id()))
    if row is None:
        row = StickyRolesConfig(guild_id=guild_id())
        db.add(row)
    row.excluded_role_ids_json = json.dumps(body.excluded_role_ids)
    row.enabled = body.enabled
    db.commit()
    return get_config(db)


@router.get("/saved")
def saved(db: Session = Depends(get_db)) -> list[dict]:
    return [{"user_id": row.user_id, "role_ids": json.loads(row.role_ids_json), "saved_at": row.saved_at}
            for row in db.scalars(select(StickyRolesSaved).where(StickyRolesSaved.guild_id == guild_id())
                                  .order_by(StickyRolesSaved.saved_at.desc()).limit(100))]
