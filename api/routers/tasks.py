from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import BotTask
from routers.common import enqueue, guild_id
from schemas import TaskInput

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("")
def create(body: TaskInput, db: Session = Depends(get_db)) -> dict[str, int]:
    task = enqueue(db, body.type, body.payload)
    return {"id": task.id}


@router.get("")
def list_tasks(db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": t.id, "type": t.type, "status": t.status, "error": t.error}
            for t in db.scalars(select(BotTask).where(BotTask.guild_id == guild_id())
                                .order_by(BotTask.id.desc()).limit(50))]
