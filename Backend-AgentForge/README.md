# Backend-AgentForge

Runtime multi-tenant de agentes de **texto** para GoHighLevel (SaaS de Inofuente).
Python + FastAPI + LangChain + Supabase (Postgres/pgvector) + Redis.

## Idea central (multi-tenant)
A diferencia de un agente 1-a-1, aquí **no hay un prompt hardcodeado**. Cada sub-cuenta de
GHL configura su agente desde el frontend; la config se guarda en Supabase y el runtime la
**carga dinámicamente** por cada mensaje entrante. Un solo servicio sirve a todos los clientes.

## Flujo de un mensaje
```
GHL InboundMessage ──▶ app/api/webhooks.py   (responde rápido, encola)
                          │
                          ▼
                   app/buffer/debounce.py     (concatena mensajes seguidos en Redis)
                          │
                          ▼
                   app/workers/processor.py   (consume la cola, async)
                          │
                          ▼
                   app/core/runtime.py        (orquesta 1 turno end-to-end)
                     ├─ agent_factory: arma el agente con la config del tenant
                     ├─ chat_history: historial de la conversación
                     ├─ RAG: retrieval del knowledge base (pgvector)
                     ├─ tools: acciones GHL (agendar, tags, custom fields)
                     └─ integrations/ghl: envía la respuesta a GHL
```

## Estructura (convención modular adaptada a SaaS)
| Carpeta | Responsabilidad |
|---|---|
| `app/api/` | Endpoints HTTP: webhooks GHL, OAuth, CRUD de agentes |
| `app/core/` | `agent_factory.py` (construye el agente por tenant) + `runtime.py` (orquesta 1 turno) |
| `app/buffer/` | Debounce/concatenación de mensajes con Redis |
| `app/workers/` | Workers async que consumen la cola |
| `app/chat_history/` | Persistencia de la conversación (intercambiable) |
| `app/RAG/` | Pipeline de **indexación** del knowledge base |
| `app/tools/` | Una tool por archivo (acciones del agente sobre GHL) |
| `app/integrations/ghl/` | Cliente de la API de GoHighLevel + OAuth |
| `app/models/` | Schemas Pydantic + tipos de DB |
| `app/db/` | Cliente Supabase |
| `model_config/` | Defaults del LLM (override por tenant en DB) |
| `prompt/` | Plantilla base del system prompt (override por tenant en DB) |
| `migrations/` | SQL del esquema de Supabase (con RLS) |

## Arranque local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar credenciales
uvicorn app.main:app --reload
```
