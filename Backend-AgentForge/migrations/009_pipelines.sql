-- AgentForge — migración 009: Embudos (pipelines) y enrutamiento por etapa.
-- Un agente atiende según la etapa del lead en el embudo de GHL.

-- Cache de pipelines/etapas de GHL (para selectores y resolver nombres sin llamar
-- a GHL en cada mensaje). Se refresca desde la pestaña Embudos.
create table if not exists agentforge_pipelines (
  id          uuid primary key default gen_random_uuid(),
  location_id uuid not null references agentforge_locations(id) on delete cascade,
  pipeline_id text not null,
  name        text,
  stages      jsonb not null default '[]',   -- [{id, name, position}]
  updated_at  timestamptz default now(),
  unique (location_id, pipeline_id)
);

-- Ruteo: qué agente atiende en cada etapa.
create table if not exists agentforge_stage_routes (
  id          uuid primary key default gen_random_uuid(),
  location_id uuid not null references agentforge_locations(id) on delete cascade,
  pipeline_id text not null,
  stage_id    text not null,
  agent_id    uuid references agentforge_agents(id) on delete cascade,
  unique (location_id, pipeline_id, stage_id)
);
