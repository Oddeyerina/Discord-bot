import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import require_session
from database import Base, engine, migrate_phase_b, migrate_ticket_columns
import models  # noqa: F401
from routers import auth, guild_data, honeypot, levels, panels, reaction_roles, remembering, stats, sticky, sticky_roles, tasks, tempvoice, tickets, welcome


@asynccontextmanager
async def lifespan(_: FastAPI):
    if len(os.getenv("SESSION_SECRET", "")) < 32:
        raise RuntimeError("SESSION_SECRET must contain at least 32 characters")
    Base.metadata.create_all(engine)
    migrate_ticket_columns()
    migrate_phase_b()
    yield


app = FastAPI(title="dcbot-suite API", lifespan=lifespan)
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
               tempvoice.router, sticky_roles.router, remembering.router, stats.router, tasks.router):
    app.include_router(router, dependencies=[Depends(require_session)])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
