"""Central audit recording for successful dashboard writes."""

import json
import os
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from auth import require_session
from models import AuditLog
from routers.common import guild_id


def log_action(db: Session, action: str, target: str, details: dict[str, Any],
               request: Request | None = None) -> None:
    username = require_session(request) if request is not None else os.getenv("DASHBOARD_USER", "admin")
    actor_id = os.getenv("DASHBOARD_DISCORD_USER_ID") or username
    db.add(AuditLog(guild_id=guild_id(), actor_id=actor_id, action=action,
                    target=target, details_json=json.dumps(details)))
    db.commit()
