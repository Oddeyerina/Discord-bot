import os
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from audit import log_action
from auth import require_session
from database import Base, SessionLocal, engine, migrate_phase_b, migrate_phase_c, migrate_ticket_columns
import models  # noqa: F401
from routers import audit, auth, dashboard, guild_data, health, honeypot, levels, moderation, panels, reaction_roles, remembering, stats, sticky, sticky_roles, tasks, tempvoice, tickets, verification, welcome

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if len(os.getenv("SESSION_SECRET", "")) < 32:
        raise RuntimeError("SESSION_SECRET must contain at least 32 characters")
    Base.metadata.create_all(engine)
    migrate_ticket_columns()
    migrate_phase_b()
    migrate_phase_c()
    yield


app = FastAPI(title="dcbot-suite API", lifespan=lifespan)


@app.middleware("http")
async def record_dashboard_write(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/") and request.method in {"POST", "PUT", "DELETE"} and response.status_code < 400:
        parts = path.strip("/").split("/")
        feature = parts[1] if len(parts) > 1 else "unknown"
        operation = {"POST": "create", "PUT": "update", "DELETE": "delete"}[request.method]
        if feature in {"tickets", "reaction-roles"} and "config" in parts:
            action = f"{'reactionroles' if feature == 'reaction-roles' else 'ticket'}.panel.{operation}"
        else:
            action = f"{feature}.{operation}"
        try:
            with SessionLocal() as db:
                log_action(db, action, parts[-1], {"path": path, "method": request.method},
                           request=None if path == "/api/auth/login" else request)
        except Exception:
            log.exception("Could not record audit entry for %s", path)
    return response
app.add_middleware(
    CORSMiddleware,
    # WEB_ORIGIN must exactly match the browser's dashboard URL so its session cookie is sent.
    allow_origins=[os.environ["WEB_ORIGIN"]],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.include_router(auth.router)
app.include_router(guild_data.internal_router)
for router in (guild_data.router, panels.router, tickets.router, honeypot.router,
               levels.router, reaction_roles.router, welcome.router, sticky.router,
               tempvoice.router, sticky_roles.router, remembering.router, stats.router,
               moderation.router, verification.router, health.router, audit.router,
               dashboard.router, tasks.router):
    app.include_router(router, dependencies=[Depends(require_session)])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
