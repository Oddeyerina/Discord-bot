import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Ticket, TicketAutoresponse, TicketPriority, TicketQuickreply, TicketReason
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
    gid = guild_id()
    result["priorities"] = [
        {"id": row.id, "label": row.label, "emoji": row.emoji, "color": row.color}
        for row in db.scalars(select(TicketPriority).where(TicketPriority.guild_id == gid,
                    TicketPriority.active.is_(True)).order_by(TicketPriority.position))]
    result["autoresponses"] = [
        {"trigger_keyword": row.trigger_keyword, "response_text": row.response_text, "enabled": row.enabled}
        for row in db.scalars(select(TicketAutoresponse).where(TicketAutoresponse.guild_id == gid,
                    TicketAutoresponse.panel_id == (panel.id if panel else None)).order_by(TicketAutoresponse.position))]
    result["quickreplies"] = [
        {"label": row.label, "response_text": row.response_text}
        for row in db.scalars(select(TicketQuickreply).where(TicketQuickreply.guild_id == gid)
                              .order_by(TicketQuickreply.position))]
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
    priorities = {row.id: row for row in db.scalars(select(TicketPriority).where(TicketPriority.guild_id == guild_id()))}
    for row in priorities.values():
        row.active = False
    for pos, priority in enumerate(body.priorities):
        row = priorities.get(priority.id) if priority.id is not None else None
        if row is None:
            row = TicketPriority(guild_id=guild_id())
            db.add(row)
        row.label = priority.label
        row.emoji = priority.emoji
        row.color = priority.color
        row.position = pos
        row.active = True
    for model in (TicketAutoresponse, TicketQuickreply):
        query = select(model).where(model.guild_id == guild_id())
        if model is TicketAutoresponse:
            query = query.where(model.panel_id == panel.id)
        for row in db.scalars(query):
            db.delete(row)
    db.flush()
    for pos, item in enumerate(body.autoresponses):
        db.add(TicketAutoresponse(guild_id=guild_id(), panel_id=panel.id,
                                  trigger_keyword=item.trigger_keyword, response_text=item.response_text,
                                  position=pos, enabled=item.enabled))
    for pos, item in enumerate(body.quickreplies):
        db.add(TicketQuickreply(guild_id=guild_id(), label=item.label,
                                response_text=item.response_text, position=pos))
    db.commit()
    return get_config(db)


@router.get("", response_model=list[TicketRecord])
def list_tickets(db: Session = Depends(get_db)) -> list[TicketRecord]:
    return [TicketRecord.model_validate(ticket) for ticket in
            db.scalars(select(Ticket).where(Ticket.guild_id == guild_id())
                       .order_by(Ticket.id.desc()).limit(100))]
