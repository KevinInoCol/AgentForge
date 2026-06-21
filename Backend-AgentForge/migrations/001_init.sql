-- AgentForge — esquema inicial (Postgres + pgvector)
-- Todas las tablas usan prefijo `agentforge_` para no chocar con tablas existentes.
-- Tenancy: ARIA es la única agencia. El tenant operativo es la sub-cuenta GHL (location).

create extension if not exists vector;

-- ── Sub-cuentas de GHL (el tenant) ───────────────────────────────
-- MVP: autenticación con Private Integration Token (PIT) por sub-cuenta.
-- Workspace = tenant. Puede existir SOLO con OpenAI key (para construir/probar).
-- El ghl_location_id + PIT se conectan al Publicar (go-live).
create table if not exists agentforge_locations (
  id            uuid primary key default gen_random_uuid(),
  ghl_location_id text unique,      -- nullable: se setea al conectar GHL
  name          text,
  private_integration_token text,   -- PIT (cifrar en producción)
  openai_api_key text,              -- API key de OpenAI del cliente (cifrar en producción)
  default_model  text default 'gpt-4.1',
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
  published     boolean not null default false,  -- borrador vs publicado (go-live)
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
