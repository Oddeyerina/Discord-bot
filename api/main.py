import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import require_session
from database import Base, engine, migrate_ticket_timestamps
import models  # noqa: F401
from routers import auth, guild_data, honeypot, levels, panels, reaction_roles, tasks, tickets, welcome


@asynccontextmanager
async def lifespan(_: FastAPI):
    if len(os.getenv("SESSION_SECRET", "")) < 32:
        raise RuntimeError("SESSION_SECRET must contain at least 32 characters")
    Base.metadata.create_all(engine)
    migrate_ticket_timestamps()
    yield


app = FastAPI(title="dcbot-suite API", lifespan=lifespan)
origin = os.environ["NEXT_PUBLIC_API_BASE_URL"]
parsed_origin = urlsplit(origin)
web_origin = f"{parsed_origin.scheme}://{parsed_origin.hostname}:{os.environ['WEB_HOST_PORT']}"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[web_origin, "http://localhost:" + os.environ["WEB_HOST_PORT"]],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(auth.router)
app.include_router(guild_data.internal_router)
for router in (guild_data.router, panels.router, tickets.router, honeypot.router,
               levels.router, reaction_roles.router, welcome.router, tasks.router):
    app.include_router(router, dependencies=[Depends(require_session)])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
