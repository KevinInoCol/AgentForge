# Base de Datos — AgentForge (Supabase / Postgres + pgvector)

Documento único de referencia de TODO lo de base de datos. Si en el futuro
cambiamos o mejoramos algo, aquí está el registro completo.

**Convenciones**
- Todas las tablas llevan prefijo **`agentforge_`** (para no chocar con otras tablas del proyecto).
- El backend usa la **service_role key** → ignora RLS. El frontend NO consulta Supabase directo (pasa por la API), así que **RLS no es necesario** en el MVP.
- Búsqueda vectorial vía función RPC (`match_agentforge_chunks`) → **no se necesita `DATABASE_URL`**.
- Embeddings: `text-embedding-3-small` → **vector(1536)**.

---

## A) Esquema completo actual (instalación desde cero)

Para un proyecto Supabase **nuevo**, corre TODO este bloque en **SQL Editor**.
Es idempotente (se puede correr varias veces). Refleja el estado tras las migraciones 001–005.

```sql
-- Extensión para embeddings
create extension if not exists vector;

-- ── Workspaces (tenant) ──────────────────────────────────────────
-- Un workspace por usuario. Puede existir solo con OpenAI key (para construir/probar).
-- ghl_location_id + PIT se conectan al Publicar (go-live).
create table if not exists agentforge_locations (
  id              uuid primary key default gen_random_uuid(),
  ghl_location_id text unique,                 -- nullable: se setea al conectar GHL
  name            text,
  private_integration_token text,              -- PIT (cifrar en producción)
  openai_api_key  text,                        -- key de OpenAI del cliente (cifrar en producción)
  default_model   text default 'gpt-4.1',
  owner_user_id   uuid,                         -- dueño (Supabase Auth user id)
  created_at      timestamptz default now()
);
create index if not exists agentforge_locations_owner_idx
  on agentforge_locations (owner_user_id);

-- ── Agentes ──────────────────────────────────────────────────────
create table if not exists agentforge_agents (
  id            uuid primary key default gen_random_uuid(),
  location_id   uuid not null references agentforge_locations(id) on delete cascade,
  name          text not null,
  system_prompt text not null,
  model         text not null default 'gpt-4.1',
  temperature   real not null default 0,
  enabled       boolean not null default true,
  published     boolean not null default false,  -- borrador vs publicado (go-live)
  tools         text[] not null default '{}',
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- updated_at automático en cada UPDATE
create or replace function agentforge_set_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

drop trigger if exists agentforge_agents_set_updated_at on agentforge_agents;
create trigger agentforge_agents_set_updated_at
  before update on agentforge_agents
  for each row execute function agentforge_set_updated_at();

-- ── Base de conocimiento (RAG) ───────────────────────────────────
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
  id             uuid primary key default gen_random_uuid(),
  location_id    uuid not null references agentforge_locations(id) on delete cascade,
  agent_id       uuid references agentforge_agents(id) on delete set null,
  ghl_contact_id text not null,
  human_handoff  boolean not null default false,  -- pausa la IA
  created_at     timestamptz default now(),
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

-- ── Metering (para billing/rebilling futuro) ─────────────────────
create table if not exists agentforge_usage_events (
  id           uuid primary key default gen_random_uuid(),
  location_id  uuid not null references agentforge_locations(id) on delete cascade,
  agent_id     uuid references agentforge_agents(id) on delete set null,
  kind         text not null,        -- 'message' | 'tokens' | ...
  quantity     int not null default 0,
  created_at   timestamptz default now()
);

-- ── Búsqueda por similitud (RAG) ─────────────────────────────────
create or replace function match_agentforge_chunks(
  p_agent_id uuid,
  p_query_embedding vector(1536),
  p_match_count int default 5
)
returns table (id uuid, content text, similarity float)
language sql stable
as $$
  select c.id, c.content, 1 - (c.embedding <=> p_query_embedding) as similarity
  from agentforge_knowledge_chunks c
  where c.agent_id = p_agent_id
  order by c.embedding <=> p_query_embedding
  limit p_match_count;
$$;
```

---

## B) Historial de migraciones

Orden cronológico de lo que se ejecutó en Supabase. Los archivos `.sql` están en `migrations/`.

### 001 — Esquema inicial (`001_init.sql`)
Tablas base con prefijo `agentforge_` + extensión `vector` + trigger `updated_at`.
Creó: locations, agents, knowledge_documents, knowledge_chunks, conversations, messages, usage_events.

### 002 — OpenAI por sub-cuenta (`002_openai_settings.sql`)
```sql
alter table agentforge_locations
  add column if not exists openai_api_key text,
  add column if not exists default_model text default 'gpt-4.1';
```
**Por qué:** cada cliente pone su propia API key de OpenAI (paga su consumo) + modelo por defecto.

### 003 — Desacoplar workspace de GHL (`003_workspace_decouple.sql`)
```sql
alter table agentforge_locations alter column ghl_location_id drop not null;
alter table agentforge_agents
  add column if not exists published boolean not null default false;
```
**Por qué:** poder construir/probar agentes con solo la OpenAI key (sin GHL). El `published` separa borrador de "en vivo"; el GHL se conecta al Publicar.

### 004 — Dueño del workspace / Auth (`004_auth_owner.sql`)
```sql
alter table agentforge_locations
  add column if not exists owner_user_id uuid;
create index if not exists agentforge_locations_owner_idx
  on agentforge_locations (owner_user_id);
```
**Por qué:** login con Supabase Auth; cada usuario tiene su propio workspace aislado.

### 005 — Búsqueda de conocimiento (`005_knowledge_search.sql`)
La función `match_agentforge_chunks` (ver bloque en la sección A).
**Por qué:** retrieval del RAG por similitud (pgvector), llamada como tool "Base de Conocimiento" desde el backend vía `supabase.rpc(...)`.

---

## C) Verificación rápida

```sql
-- Tablas creadas
select table_name from information_schema.tables
where table_name like 'agentforge_%' order by table_name;

-- Columnas de locations (debe incluir openai_api_key, default_model, owner_user_id; ghl_location_id nullable)
select column_name, is_nullable from information_schema.columns
where table_name = 'agentforge_locations' order by column_name;

-- Función de búsqueda
select proname from pg_proc where proname = 'match_agentforge_chunks';
```

---

## D) RLS (opcional, futuro)
Hoy NO se usa (el backend va con service_role). Si algún día el frontend consulta
Supabase directo, activar RLS y definir políticas por `owner_user_id` / `location_id`.

---

## Notas de seguridad (pendientes para producción)
- El **PIT** y la **OpenAI key** se guardan en texto plano. Cifrar (o usar Supabase Vault).
- Considerar RLS si el frontend llega a consultar Supabase directo.
