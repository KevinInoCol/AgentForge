"""Entrypoint FastAPI. Solo monta routers — sin lógica de negocio."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, oauth, webhooks, workspaces

app = FastAPI(title="AgentForge API", version="0.1.0")

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


@app.get("/health")
def health():
    return {"status": "ok"}
