"""Read-only data for the dashboard overview."""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from database import get_db
from models import AppMeta, AuditLog, BotTask, Ticket, TicketReason, WarningRecord
from routers.common import guild_id

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)) -> dict:
    gid = guild_id()
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    today = now.date()
    first_day = today - timedelta(days=6)

    open_tickets = db.scalar(select(func.count()).select_from(Ticket).where(
        Ticket.guild_id == gid, Ticket.status == "open")) or 0
    tickets_7d = db.scalar(select(func.count()).select_from(Ticket).where(
        Ticket.guild_id == gid, Ticket.status == "closed",
        Ticket.closed_at >= seven_days_ago)) or 0
    counts = dict(db.execute(select(func.date(Ticket.created_at), func.count()).where(
        Ticket.guild_id == gid, Ticket.created_at >= first_day).group_by(
        func.date(Ticket.created_at))).all())
    chart = [{"date": (first_day + timedelta(days=offset)).isoformat(),
              "opened": int(counts.get((first_day + timedelta(days=offset)).isoformat(), 0))}
             for offset in range(7)]

    ticket_rows = db.execute(select(Ticket, TicketReason.label).outerjoin(
        TicketReason, Ticket.reason_id == TicketReason.id).where(
        Ticket.guild_id == gid).order_by(Ticket.id.desc()).limit(5)).all()
    recent_tickets = [{"id": ticket.id, "guild_id": ticket.guild_id,
                       "thread_id": ticket.thread_id,
                       "user_id": ticket.user_id, "reason": label or "Unknown reason",
                       "status": ticket.status, "created_at": ticket.created_at}
                      for ticket, label in ticket_rows]
    recent_tasks = [{"id": task.id, "type": task.type, "status": task.status,
                     "error": task.error, "created_at": task.created_at}
                    for task in db.scalars(select(BotTask).where(
                        BotTask.guild_id == gid).order_by(BotTask.id.desc()).limit(5))]

    tables = inspect(db.bind).get_table_names()
    audit_available = "audit_log" in tables
    warnings_available = "warnings" in tables
    recent_audit = ([{"id": row.id, "actor_id": row.actor_id,
                      "action": row.action, "target": row.target,
                      "created_at": row.created_at}
                     for row in db.scalars(select(AuditLog).where(
                         AuditLog.guild_id == gid).order_by(AuditLog.id.desc()).limit(5))]
                    if audit_available else [])
    recent_warnings = ([{"id": row.id, "user_id": row.user_id,
                         "moderator_id": row.moderator_id, "reason": row.reason,
                         "created_at": row.created_at}
                        for row in db.scalars(select(WarningRecord).where(
                            WarningRecord.guild_id == gid).order_by(WarningRecord.id.desc()).limit(5))]
                       if warnings_available else [])

    online = in_voice = total = None
    bot_status = "offline"
    heartbeat = db.get(AppMeta, "bot_heartbeat")
    if heartbeat:
        try:
            snapshot = json.loads(heartbeat.value)
            seen = datetime.fromisoformat(snapshot["last_seen"])
            if seen.tzinfo is None:
                seen = seen.replace(tzinfo=timezone.utc)
            if snapshot.get("guild_id") == gid and timedelta(0) <= now - seen <= timedelta(seconds=120):
                bot_status = "online"
                online = snapshot.get("members_online")
                in_voice = snapshot.get("in_voice")
                total = snapshot.get("total_members")
        except (ValueError, KeyError, TypeError):
            pass

    return {
        "tiles": {"members_online": online, "in_voice": in_voice,
                  "total_members": total, "open_tickets": open_tickets,
                  "tickets_7d": tickets_7d, "bot_status": bot_status},
        "chart": chart,
        "recent_tickets": recent_tickets,
        "recent_tasks": recent_tasks,
        "recent_audit": recent_audit,
        "recent_warnings": recent_warnings,
        "sections": {"audit": audit_available, "warnings": warnings_available},
    }
