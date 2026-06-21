# Setup de Supabase — AgentForge

Sí, **las tablas son necesarias**: todo el backend (agentes, conversaciones, credenciales de HighLevel, knowledge base, metering) lee y escribe en Supabase. Sigue estos pasos una sola vez.

> El mismo SQL vive en [`migrations/001_init.sql`](./migrations/001_init.sql). Esta guía es para ejecutarlo cómodo desde el panel de Supabase.

---

## 1. Crear el proyecto y obtener las llaves

1. Entra a [supabase.com](https://supabase.com) → **New project**.
2. Cuando esté listo, ve a **Project Settings → API** y copia:
   - **Project URL** → variable `SUPABASE_URL`
   - **service_role key** (la secreta, NO la `anon`) → variable `SUPABASE_SERVICE_ROLE_KEY`
3. Ve a **Project Settings → Database → Connection string → URI** y copia esa cadena → variable `DATABASE_URL` (la usa pgvector para el RAG).

Pega esos 3 valores en `Backend-AgentForge/.env` (ver `.env.example`).

---

## 2. Crear las tablas

En el panel de Supabase: **SQL Editor → New query**, pega TODO el bloque de abajo y dale **Run**.

> Todas las tablas llevan prefijo **`agentforge_`** para que no choquen con tus tablas existentes. El script es **idempotente** (`create table if not exists`): puedes correrlo varias veces sin error.

```sql
-- AgentForge — esquema inicial (Postgres + pgvector)
-- Todas las tablas usan prefijo `agentforge_` para no chocar con tablas existentes.

create extension if not exists vector;

-- ── Sub-cuentas de GHL (el tenant) ───────────────────────────────
create table if not exists agentforge_locations (
  id            uuid primary key default gen_random_uuid(),
  ghl_location_id text unique not null,
  name          text,
  private_integration_token text,   -- PIT (cifrar en producción)
  created_at    timestamptz default now()
);

-- ── Agentes (config que el cliente edita en el frontend) ─────────
create table if not exists agentforge_agents (
  id            uuid primary key default gen_random_uuid(),
  location_id   uuid not null references agentforge_locations(id) on delete cascade,
  name          text not null,
  system_prompt text not null,
  model         text not null default 'gpt-4.1',
  temperature   real not null default 0,
  enabled       boolean not null default true,
  tools         text[] not null default '{}',
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- Mantener updated_at al día en cada UPDATE.
create or replace function agentforge_set_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

drop trigger if exists agentforge_agents_set_updated_at on agentforge_agents;
create trigger agentforge_agents_set_updated_at
  before update on agentforge_agents
  for each row execute function agentforge_set_updated_at();

-- ── Knowledge base (RAG por agente) ──────────────────────────────
create table if not exists agentforge_knowledge_documents (
  id          uuid primary key default gen_random_uuid(),
  agent_id    uuid not null references agentforge_agents(id) on delete cascade,
  filename    text not null,
  created_at  timestamptz default now()
);

create table if not exists agentforge_knowledge_chunks (
  id          uuid primary key default gen_random_uuid(),
  agent_id    uuid not null references agentforge_agents(id) on delete cascade,
  document_id uuid references agentforge_knowledge_documents(id) on delete cascade,
  content     text not null,
  embedding   vector(1536)
);
create index if not exists agentforge_knowledge_chunks_embedding_idx
  on agentforge_knowledge_chunks using ivfflat (embedding vector_cosine_ops);

-- ── Conversaciones y mensajes ────────────────────────────────────
create table if not exists agentforge_conversations (
  id           uuid primary key default gen_random_uuid(),
  location_id  uuid not null references agentforge_locations(id) on delete cascade,
  agent_id     uuid references agentforge_agents(id) on delete set null,
  ghl_contact_id text not null,
  human_handoff boolean not null default false,  -- pausa la IA
  created_at   timestamptz default now(),
  unique (location_id, ghl_contact_id)
);

create table if not exists agentforge_messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references agentforge_conversations(id) on delete cascade,
  role            text not null check (role in ('user','assistant','system','tool')),
  content         text not null,
  tokens          int default 0,
  created_at      timestamptz default now()
);

-- ── Metering para billing/rebilling ──────────────────────────────
create table if not exists agentforge_usage_events (
  id           uuid primary key default gen_random_uuid(),
  location_id  uuid not null references agentforge_locations(id) on delete cascade,
  agent_id     uuid references agentforge_agents(id) on delete set null,
  kind         text not null,        -- 'message' | 'tokens' | ...
  quantity     int not null default 0,
  created_at   timestamptz default now()
);
```

---

## 3. (Opcional) RLS

El backend usa la **service_role key**, que **ignora RLS** — así que las tablas funcionan sin políticas. El frontend NO consulta Supabase directo (pasa siempre por la API del backend), por lo que **no necesitas RLS para el MVP**.

Si en el futuro el frontend leyera Supabase directo, activa RLS y define políticas por `location_id`:

```sql
alter table agentforge_agents enable row level security;
alter table agentforge_conversations enable row level security;
alter table agentforge_messages enable row level security;
alter table agentforge_knowledge_documents enable row level security;
alter table agentforge_knowledge_chunks enable row level security;
-- + políticas según cómo autentiques el frontend (JWT de GHL / Supabase Auth).
```

---

## 4. Verificar

En **Table Editor** deberías ver 7 tablas con prefijo: `agentforge_locations`, `agentforge_agents`, `agentforge_knowledge_documents`, `agentforge_knowledge_chunks`, `agentforge_conversations`, `agentforge_messages`, `agentforge_usage_events`.

**No necesitas insertar filas a mano.** Desde el panel de AgentForge:
- **🔑 Credenciales HighLevel** → crea la fila en `locations` (con tu LocationID + PIT).
- **+ Crear asistente** → crea filas en `agents`.

---

## 5. Resumen de variables de entorno

`Backend-AgentForge/.env`:
```env
OPENAI_API_KEY=...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...        # service_role (secreta)
DATABASE_URL=postgresql://postgres:...   # para pgvector
REDIS_URL=redis://localhost:6379/0
```

`Frontend-AgentForge/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
# (el frontend NO necesita llaves de Supabase en el MVP)
```
