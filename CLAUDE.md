# AgentForge

SaaS **multi-tenant** de Inofuente (proyecto personal): agentes de IA de texto para **GoHighLevel (GHL)**. Cada
sub-cuenta de GHL configura su propio agente desde el frontend (sin prompt hardcodeado);
un solo backend sirve a todos los clientes cargando la config del tenant dinámicamente por
cada mensaje entrante.

## Monorepo (2 apps)

- **`Backend-AgentForge/`** — Python + FastAPI + LangChain/LangGraph + Supabase (Postgres/pgvector) + Redis
- **`Frontend-AgentForge/`** — Next.js (App Router) + TypeScript + `@supabase/supabase-js`

## Flujo de un mensaje (runtime)

```
Webhook GHL (app/api/webhooks.py) → responde rápido, encola
  → Debounce en Redis (app/buffer/) — concatena mensajes seguidos
  → Worker async (app/workers/) consume la cola
  → app/core/runtime.py orquesta 1 turno:
      agent_factory (arma agente del tenant) + chat_history + RAG (pgvector) + tools GHL
  → integrations/ghl envía la respuesta a GHL
```

## Backend — mapa

| Ruta | Responsabilidad |
|---|---|
| `app/api/` | `webhooks.py`, `oauth.py`, `agents.py`, `workspaces.py` |
| `app/core/` | `agent_factory.py`, `runtime.py`, `agent_generator.py`, `analysis.py`, `followups.py`, `transcription.py` |
| `app/buffer/` | Debounce/concatenación con Redis |
| `app/workers/` | Workers async (consumen la cola) |
| `app/chat_history/` | Persistencia de conversación |
| `app/RAG/` | Pipeline de indexación del knowledge base |
| `app/tools/` | `catalog.py` (registro único + `build_tools_for_agent`), `calendar.py`, `ghl_actions.py`, `knowledge.py` |
| `app/integrations/ghl/` | Cliente API GoHighLevel + OAuth |
| `app/integrations/google/` | OAuth Google + cliente Calendar (para tools conectables) |
| `app/db/` | Cliente Supabase (usa **service_role key** → ignora RLS) |
| `model_config/` | Defaults del LLM (override por tenant en DB) |
| `prompt/` | Plantilla base del system prompt (override por tenant en DB) |
| `migrations/` | SQL del esquema Supabase (001–010) |

## Base de datos

- Fuente única de verdad: **`Backend-AgentForge/DATABASE.md`** (léelo antes de tocar esquema).
- Todas las tablas con prefijo **`agentforge_`**.
- El frontend **no** consulta Supabase directo → pasa por la API (por eso RLS no es crítico en el MVP).
- Búsqueda vectorial por RPC `match_agentforge_chunks`. Embeddings `text-embedding-3-large`
  truncado a **1536 dims** → `vector(1536)` + ivfflat. Si cambias el modelo de embeddings, **re-indexa**.
- Para aplicar migraciones nuevas: `Backend-AgentForge/migrations/ACTUALIZAR_BD.md`.

## Frontend — módulos (`src/app/`)

`agents`, `analisis`, `contacts`, `credentials`, `embudos`, `inbox`, `openai`, `planes`, `settings`, `tags`, `login`.

## Arranque local

```bash
# Backend
cd Backend-AgentForge
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar credenciales
uvicorn app.main:app --reload

# Frontend
cd Frontend-AgentForge
npm install && npm run dev
```

Deploy: EasyPanel (ver `DEPLOY_EASYPANEL.md`). Setup Supabase: `SUPABASE_SETUP.md`.

## Sistema de tools (extensibilidad de agentes)

- **Catálogo único** en `app/tools/catalog.py`: cada tool habilitable es un `ToolSpec` (key, label, description, `provider` opcional, `factory(ctx)`). `build_tools_for_agent(agent_row, location, api_key)` es el ÚNICO ensamblador — lo usan `runtime.py` y `agents.py` (chat lab).
- **Base de Conocimiento**: automática si el agente tiene documentos (no se habilita a mano).
- **Tools con conexión (Nivel 2)**: `provider != None` → requieren una fila activa en `agentforge_connections` (OAuth del tenant). Si no hay conexión, la tool se omite sin romper el turno.
- **Google Calendar**: primer proveedor OAuth. Flujo en `api/connections.py` (`/google/start`, autenticado, firma un `state`) + `api/oauth.py` (`/oauth/google/callback`, sin sesión, confía en el `state`). Tokens cifrados con Fernet (`core/crypto.py`, `ENCRYPTION_KEY`).
- **Agregar una tool**: registrar un `ToolSpec` en el catálogo. Nada más cambia.
- Env nuevas: `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI`, `ENCRYPTION_KEY`, `FRONTEND_URL` (ver `.env.example`).

## Historial de features (commits versionados)

- **v1.8.0** — Conexiones + tools: catálogo de tools, `build_tools_for_agent`, Google Calendar vía OAuth (agendar/consultar disponibilidad), credenciales cifradas. Migración 011.
- **v1.7.0** — Análisis de Conversaciones: por qué el contacto no avanzó (auto con Agente de Seguimiento IA + botón manual). `core/analysis.py`, migración 010.
- **v1.6.0** — Embudos: enrutamiento por etapa de GHL (agente distinto por etapa del pipeline). Migración 009.
- **v1.5.0** — Modo de seguimiento: mensajes fijos (sin tokens) o Agente de Seguimiento IA. Migración 008.
- **v1.4.0** — Remarketing/Seguimientos: scheduler APScheduler (4/8/12h), cancela al responder. Migración 007.

## Convenciones

- Commits versionados con tag `vX.Y.Z:` y descripción en español.
- Documentación y comentarios en **español**.
