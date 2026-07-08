# Base de Datos — AgentForge (Supabase / Postgres + pgvector)

Documento único de referencia de TODO lo de base de datos. Si en el futuro
cambiamos o mejoramos algo, aquí está el registro completo.

**Convenciones**
- Todas las tablas llevan prefijo **`agentforge_`** (para no chocar con otras tablas del proyecto).
- El backend usa la **service_role key** → ignora RLS. El frontend NO consulta Supabase directo (pasa por la API), así que **RLS no es necesario** en el MVP.
- Búsqueda vectorial vía función RPC (`match_agentforge_chunks`) → **no se necesita `DATABASE_URL`**.
- Embeddings: `text-embedding-3-large` **truncado a 1536 dims** (param `dimensions`) → columna **vector(1536)** + índice ivfflat (límite 2000 dims). Si cambias el modelo de embeddings, **re-indexa** los documentos (los vectores de modelos distintos no son comparables).

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
  followups_enabled boolean not null default false,   -- remarketing on/off
  followup_messages text[] not null default '{}',     -- 3 mensajes fijos (4/8/12h)
  followup_mode text not null default 'fixed',         -- 'fixed' | 'ai'
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
  contact_name   text,                              -- nombre del contacto (de GHL)
  human_handoff  boolean not null default false,    -- pausa la IA
  channel        text,                              -- canal para responder (FB/WhatsApp/SMS)
  last_inbound_at    timestamptz,                   -- último mensaje del contacto
  followup_anchor_at timestamptz,                   -- inicio del reloj de seguimiento
  followups_sent     int not null default 0,        -- seguimientos enviados en el ciclo
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

-- ── Contactos del workspace (con métricas) ───────────────────────
create or replace function agentforge_workspace_contacts(p_workspace_id uuid)
returns table (conversation_id uuid, ghl_contact_id text, contact_name text,
               agent_name text, interactions int, last_at timestamptz)
language sql stable as $$
  select c.id, c.ghl_contact_id, c.contact_name, a.name,
         count(m.id)::int, max(m.created_at)
  from agentforge_conversations c
  left join agentforge_agents a   on a.id = c.agent_id
  left join agentforge_messages m on m.conversation_id = c.id
  where c.location_id = p_workspace_id
  group by c.id, c.ghl_contact_id, c.contact_name, a.name
  order by max(m.created_at) desc nulls last;
$$;

-- ── Seguimientos pendientes (remarketing) ────────────────────────
drop function if exists agentforge_due_followups();
create or replace function agentforge_due_followups()
returns table (conversation_id uuid, ghl_contact_id text, channel text, pit text,
               followups_sent int, followup_anchor_at timestamptz, followup_mode text,
               followup_messages text[], openai_api_key text,
               agent_system_prompt text, agent_model text)
language sql stable as $$
  select c.id, c.ghl_contact_id, c.channel, l.private_integration_token,
         c.followups_sent, c.followup_anchor_at, a.followup_mode, a.followup_messages,
         l.openai_api_key, a.system_prompt, a.model
  from agentforge_conversations c
  join agentforge_agents a    on a.id = c.agent_id
  join agentforge_locations l on l.id = c.location_id
  where a.followups_enabled = true and a.published = true
    and c.followup_anchor_at is not null
    and l.private_integration_token is not null
    and c.followups_sent < 3
    and (c.last_inbound_at is null or c.last_inbound_at <= c.followup_anchor_at);
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

### 006 — Contactos + métricas (`006_contacts.sql`)
```sql
alter table agentforge_conversations add column if not exists contact_name text;
-- + función agentforge_workspace_contacts(p_workspace_id) (ver sección A)
```
**Por qué:** pestaña Contactos con nombre del contacto, agente y nº de interacciones.

### 007 — Remarketing / seguimientos (`007_remarketing.sql`)
```sql
alter table agentforge_agents
  add column if not exists followups_enabled boolean not null default false,
  add column if not exists followup_messages text[] not null default '{}';
alter table agentforge_conversations
  add column if not exists followup_anchor_at timestamptz,
  add column if not exists followups_sent int not null default 0,
  add column if not exists last_inbound_at timestamptz,
  add column if not exists channel text;
-- + función agentforge_due_followups() (reemplazada en 008)
```
**Por qué:** seguimientos automáticos (4/8/12h) a contactos que no responden.

### 008 — Agente de Seguimiento / modo IA (`008_followup_agent.sql`)
```sql
alter table agentforge_agents
  add column if not exists followup_mode text not null default 'fixed';  -- 'fixed' | 'ai'
drop function if exists agentforge_due_followups();  -- cambia tipo de retorno
-- + recrear agentforge_due_followups() ampliada (ver sección A)
```
**Por qué:** dos modos de seguimiento — mensajes fijos (sin tokens) o un agente IA que
analiza la conversación y redacta un mensaje persuasivo (consume tokens del cliente).

---

### 011 — Conexiones a servicios externos (`011_connections.sql`)
```sql
create table if not exists agentforge_connections (
  id uuid primary key default gen_random_uuid(),
  location_id uuid not null references agentforge_locations(id) on delete cascade,
  provider text not null,                  -- 'google_calendar'
  status text not null default 'active',   -- 'active' | 'error' | 'revoked'
  account_email text,
  credentials text not null default '',    -- CIFRADO (Fernet) con el token OAuth
  config jsonb not null default '{}',       -- p.ej. {"calendar_id": "primary"}
  scopes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (location_id, provider)
);
```
**Por qué:** habilita **tools con OAuth** por tenant (Nivel 2). Un workspace conecta SU
cuenta de un proveedor (ej. Google Calendar); esa conexión desbloquea tools que el agente
usa (`consultar_disponibilidad`, `crear_evento`). Los tokens OAuth se guardan **cifrados**
(Fernet, clave en `ENCRYPTION_KEY`). Las tools se ensamblan en `app/tools/catalog.py`.

**Requiere en `.env`:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`,
`ENCRYPTION_KEY`, `FRONTEND_URL`.

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
  (Las **conexiones OAuth** de `agentforge_connections` SÍ se guardan cifradas con Fernet.)
- Considerar RLS si el frontend llega a consultar Supabase directo.
