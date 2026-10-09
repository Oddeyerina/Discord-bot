import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Ticket, TicketReason
from routers.common import guild_id, panel_data, panel_for, save_panel
from schemas import TicketInput, TicketRecord

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    panel = panel_for(db, "tickets")
    result = panel_data(panel)
    result["reasons"] = [] if panel is None else [
        {"id": r.id, "label": r.label, "emoji": r.emoji, "description": r.description,
         "support_role_ids": json.loads(r.support_role_ids_json), "questions": json.loads(r.questions_json)}
        for r in db.scalars(select(TicketReason).where(TicketReason.panel_id == panel.id, TicketReason.active.is_(True))
                            .order_by(TicketReason.position))]
    return result


@router.put("/config")
def put_config(body: TicketInput, db: Session = Depends(get_db)) -> dict:
    panel = save_panel(db, "tickets", body.channel_id, body.embed, body.extra_config)
    existing = {row.id: row for row in db.scalars(select(TicketReason).where(TicketReason.panel_id == panel.id))}
    for row in existing.values():
        row.active = False
    for pos, reason in enumerate(body.reasons):
        row = existing.get(reason.id) if reason.id is not None else None
        if row is not None and set(json.loads(row.support_role_ids_json)) != set(reason.support_role_ids):
            has_tickets = db.scalar(select(Ticket.id).where(Ticket.reason_id == row.id).limit(1)) is not None
            if has_tickets:
                row = None
        if row is None:
            row = TicketReason(guild_id=guild_id(), panel_id=panel.id)
            db.add(row)
        row.label = reason.label
        row.emoji = reason.emoji
        row.description = reason.description
        row.support_role_ids_json = json.dumps(reason.support_role_ids)
        row.questions_json = json.dumps(reason.questions)
        row.position = pos
        row.active = True
    db.commit()
    return get_config(db)


@router.get("", response_model=list[TicketRecord])
def list_tickets(db: Session = Depends(get_db)) -> list[TicketRecord]:
    return [TicketRecord.model_validate(ticket) for ticket in
            db.scalars(select(Ticket).where(Ticket.guild_id == guild_id())
                       .order_by(Ticket.id.desc()).limit(100))]
