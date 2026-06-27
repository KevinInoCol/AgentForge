-- AgentForge — migración 007: Remarketing (seguimientos automáticos).
-- Config por agente (3 mensajes) + estado por conversación + función de pendientes.
-- Tiempos fijos: 4h, 8h, 12h (definidos en el backend).

alter table agentforge_agents
  add column if not exists followups_enabled boolean not null default false,
  add column if not exists followup_messages text[] not null default '{}';

alter table agentforge_conversations
  add column if not exists followup_anchor_at timestamptz,  -- inicio del reloj (última respuesta real de la IA)
  add column if not exists followups_sent int not null default 0,
  add column if not exists last_inbound_at timestamptz,     -- último mensaje del contacto
  add column if not exists channel text;                    -- canal para responder (FB/WhatsApp/SMS...)

-- Conversaciones candidatas a recibir un seguimiento (el backend decide cuál según la hora).
create or replace function agentforge_due_followups()
returns table (
  conversation_id   uuid,
  ghl_contact_id    text,
  channel           text,
  pit               text,
  followups_sent    int,
  followup_anchor_at timestamptz,
  followup_messages text[]
)
language sql stable as $$
  select
    c.id, c.ghl_contact_id, c.channel, l.private_integration_token,
    c.followups_sent, c.followup_anchor_at, a.followup_messages
  from agentforge_conversations c
  join agentforge_agents a    on a.id = c.agent_id
  join agentforge_locations l on l.id = c.location_id
  where a.followups_enabled = true
    and a.published = true
    and c.followup_anchor_at is not null
    and l.private_integration_token is not null
    and c.followups_sent < coalesce(array_length(a.followup_messages, 1), 0)
    and (c.last_inbound_at is null or c.last_inbound_at <= c.followup_anchor_at);
$$;
