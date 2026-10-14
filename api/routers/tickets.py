import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Panel, Ticket, TicketAutoresponse, TicketPriority, TicketQuickreply, TicketReason
from routers.common import enqueue, guild_id, panel_data, panel_for, panel_for_id
from schemas import TicketInput, TicketRecord


router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def config_data(db: Session, panel: Panel) -> dict:
    result = panel_data(panel)
    result["reasons"] = [
        {"id": row.id, "label": row.label, "emoji": row.emoji, "description": row.description,
         "support_role_ids": json.loads(row.support_role_ids_json), "questions": json.loads(row.questions_json)}
        for row in db.scalars(select(TicketReason).where(TicketReason.panel_id == panel.id,
                    TicketReason.active.is_(True)).order_by(TicketReason.position))]
    result["priorities"] = [
        {"id": row.id, "label": row.label, "emoji": row.emoji, "color": row.color}
        for row in db.scalars(select(TicketPriority).where(TicketPriority.panel_id == panel.id,
                    TicketPriority.active.is_(True)).order_by(TicketPriority.position))]
    result["autoresponses"] = [
        {"trigger_keyword": row.trigger_keyword, "response_text": row.response_text, "enabled": row.enabled}
        for row in db.scalars(select(TicketAutoresponse).where(TicketAutoresponse.panel_id == panel.id)
                              .order_by(TicketAutoresponse.position))]
    result["quickreplies"] = [
        {"label": row.label, "response_text": row.response_text}
        for row in db.scalars(select(TicketQuickreply).where(TicketQuickreply.panel_id == panel.id)
                              .order_by(TicketQuickreply.position))]
    return result


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> list[dict]:
    panels = db.scalars(select(Panel).where(Panel.guild_id == guild_id(), Panel.type == "tickets",
                                             Panel.active.is_(True)).order_by(Panel.id)).all()
    return [config_data(db, panel) for panel in panels]


@router.get("/config/{panel_id}")
def get_one(panel_id: int, db: Session = Depends(get_db)) -> dict:
    panel = panel_for_id(db, "tickets", panel_id)
    if panel is None:
        raise HTTPException(404, "Ticket panel not found")
    return config_data(db, panel)


def save_config(db: Session, panel: Panel, body: TicketInput) -> dict:
    panel.name = body.name or None
    panel.channel_id = body.channel_id
    panel.embed_json = body.embed.model_dump_json()
    panel.extra_config_json = json.dumps(body.extra_config)
    db.flush()

    existing = {row.id: row for row in db.scalars(select(TicketReason).where(TicketReason.panel_id == panel.id))}
    for row in existing.values():
        row.active = False
    for position, reason in enumerate(body.reasons):
        row = existing.get(reason.id) if reason.id is not None else None
        if row is not None and set(json.loads(row.support_role_ids_json)) != set(reason.support_role_ids):
            if db.scalar(select(Ticket.id).where(Ticket.reason_id == row.id).limit(1)) is not None:
                row = None
        if row is None:
            row = TicketReason(guild_id=guild_id(), panel_id=panel.id)
            db.add(row)
        row.label = reason.label
        row.emoji = reason.emoji
        row.description = reason.description
        row.support_role_ids_json = json.dumps(reason.support_role_ids)
        row.questions_json = json.dumps(reason.questions)
        row.position = position
        row.active = True

    priorities = {row.id: row for row in db.scalars(select(TicketPriority).where(
        TicketPriority.panel_id == panel.id))}
    for row in priorities.values():
        row.active = False
    for position, priority in enumerate(body.priorities):
        row = priorities.get(priority.id) if priority.id is not None else None
        if row is None:
            row = TicketPriority(guild_id=guild_id(), panel_id=panel.id)
            db.add(row)
        row.label = priority.label
        row.emoji = priority.emoji
        row.color = priority.color
        row.position = position
        row.active = True

    for model in (TicketAutoresponse, TicketQuickreply):
        for row in db.scalars(select(model).where(model.panel_id == panel.id)):
            db.delete(row)
    db.flush()
    for position, item in enumerate(body.autoresponses):
        db.add(TicketAutoresponse(guild_id=guild_id(), panel_id=panel.id,
                                  trigger_keyword=item.trigger_keyword, response_text=item.response_text,
                                  position=position, enabled=item.enabled))
    for position, item in enumerate(body.quickreplies):
        db.add(TicketQuickreply(guild_id=guild_id(), panel_id=panel.id, label=item.label,
                                response_text=item.response_text, position=position))
    db.commit()
    return config_data(db, panel)


@router.post("/config")
def create_config(body: TicketInput, db: Session = Depends(get_db)) -> dict:
    panel = Panel(guild_id=guild_id(), type="tickets", channel_id=body.channel_id, active=True)
    db.add(panel)
    return save_config(db, panel, body)


@router.put("/config/{panel_id}")
def update_config(panel_id: int, body: TicketInput, db: Session = Depends(get_db)) -> dict:
    panel = panel_for_id(db, "tickets", panel_id)
    if panel is None:
        raise HTTPException(404, "Ticket panel not found")
    return save_config(db, panel, body)


@router.put("/config")
def put_legacy_config(body: TicketInput, db: Session = Depends(get_db)) -> dict:
    panel = panel_for(db, "tickets")
    if panel is None:
        panel = Panel(guild_id=guild_id(), type="tickets", channel_id=body.channel_id, active=True)
        db.add(panel)
    return save_config(db, panel, body)


@router.delete("/config/{panel_id}")
def delete_config(panel_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    panel = panel_for_id(db, "tickets", panel_id)
    if panel is None:
        raise HTTPException(404, "Ticket panel not found")
    panel.active = False
    db.commit()
    return {"task_id": enqueue(db, "delete_panel", {"panel_id": panel.id}).id}


@router.get("", response_model=list[TicketRecord])
def list_tickets(db: Session = Depends(get_db)) -> list[TicketRecord]:
    return [TicketRecord.model_validate(ticket) for ticket in
            db.scalars(select(Ticket).where(Ticket.guild_id == guild_id())
                       .order_by(Ticket.id.desc()).limit(100))]
