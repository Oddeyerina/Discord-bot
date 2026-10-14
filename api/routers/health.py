"""Authenticated detailed health status for the overview dashboard."""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from database import SessionLocal
from models import AppMeta

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/detail")
def detail() -> dict[str, str | None]:
    result: dict[str, str | None] = {
        "api": "ok", "database": "ok", "bot": "offline", "bot_last_seen": None,
    }
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            row = db.get(AppMeta, "bot_last_seen")
            if row:
                result["bot_last_seen"] = row.value
                last = datetime.fromisoformat(row.value)
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - last).total_seconds() <= 120:
                    result["bot"] = "online"
    except Exception as exc:
        result["database"] = f"error: {exc}"
    return result
