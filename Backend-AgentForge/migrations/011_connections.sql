-- AgentForge — migración 011: Conexiones a servicios externos (tools con OAuth).
-- Un workspace conecta SU cuenta de un proveedor (Google Calendar, etc.); esa
-- conexión desbloquea tools que el agente puede usar. Las credenciales (tokens
-- OAuth) se guardan CIFRADAS (Fernet) en `credentials`.

create table if not exists agentforge_connections (
  id            uuid primary key default gen_random_uuid(),
  location_id   uuid not null references agentforge_locations(id) on delete cascade,
  provider      text not null,                 -- 'google_calendar'
  status        text not null default 'active',-- 'active' | 'error' | 'revoked'
  account_email text,                           -- para mostrar "Conectado como ..."
  credentials   text not null default '',       -- blob CIFRADO (Fernet) con el token OAuth
  config        jsonb not null default '{}',    -- p.ej. {"calendar_id": "primary"}
  scopes        text,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now(),
  -- Una conexión por proveedor por workspace (por ahora). Si en el futuro se
  -- quieren varias cuentas del mismo proveedor, se quita este unique.
  unique (location_id, provider)
);

create index if not exists agentforge_connections_location_idx
  on agentforge_connections (location_id);
