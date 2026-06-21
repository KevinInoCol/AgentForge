-- AgentForge — migración 003: desacoplar el workspace de HighLevel.
-- Ahora se puede construir un agente con solo la OpenAI key; el LocationID+PIT
-- se conectan al Publicar (go-live). Corre esto si ya tienes 001/002.

-- La sub-cuenta (workspace) ya no necesita un ghl_location_id para existir.
alter table agentforge_locations alter column ghl_location_id drop not null;

-- Estado de publicación del agente (borrador vs publicado/activo en GHL).
alter table agentforge_agents
  add column if not exists published boolean not null default false;
