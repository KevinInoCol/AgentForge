"""Entrypoint FastAPI. Solo monta routers + arranca el scheduler de seguimientos."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import agents, oauth, webhooks, workspaces
from app.core.followups import run_followups

logger = logging.getLogger(__name__)

app = FastAPI(title="AgentForge API", version=__version__)

_scheduler = AsyncIOScheduler()


@app.on_event("startup")
async def _start_scheduler():
    # Job de remarketing: revisa pendientes cada 15 min.
    _scheduler.add_job(run_followups, "interval", minutes=15, id="followups", replace_existing=True)
    _scheduler.start()
    logger.warning("[scheduler] iniciado (seguimientos cada 15 min)")


@app.on_event("shutdown")
async def _stop_scheduler():
    _scheduler.shutdown(wait=False)

# El panel (Next.js) corre en otro dominio. Ajustar allow_origins en producción.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["workspaces"])


@app.get("/")
def root():
    return {"service": "AgentForge API", "version": __version__, "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}
