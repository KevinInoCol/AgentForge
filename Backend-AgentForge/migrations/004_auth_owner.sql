-- AgentForge — migración 004: dueño del workspace (Supabase Auth).
-- Cada usuario autenticado tiene su propio workspace (aislamiento por usuario).

alter table agentforge_locations
  add column if not exists owner_user_id uuid;

create index if not exists agentforge_locations_owner_idx
  on agentforge_locations (owner_user_id);
