-- AgentForge — migración 008: Agente de Seguimiento (modo IA del remarketing).
-- 'fixed' = mensajes fijos (sin tokens) · 'ai' = un agente analiza la conversación
-- y redacta un mensaje persuasivo (consume tokens del cliente).

alter table agentforge_agents
  add column if not exists followup_mode text not null default 'fixed';  -- 'fixed' | 'ai'

-- RPC ampliada: además del PIT y los mensajes fijos, devuelve lo que el modo IA
-- necesita (openai key, persona/prompt y modelo). Tope de 3 seguimientos (4/8/12h).
create or replace function agentforge_due_followups()
returns table (
  conversation_id    uuid,
  ghl_contact_id     text,
  channel            text,
  pit                text,
  followups_sent     int,
  followup_anchor_at timestamptz,
  followup_mode      text,
  followup_messages  text[],
  openai_api_key     text,
  agent_system_prompt text,
  agent_model        text
)
language sql stable as $$
  select
    c.id, c.ghl_contact_id, c.channel, l.private_integration_token,
    c.followups_sent, c.followup_anchor_at,
    a.followup_mode, a.followup_messages,
    l.openai_api_key, a.system_prompt, a.model
  from agentforge_conversations c
  join agentforge_agents a    on a.id = c.agent_id
  join agentforge_locations l on l.id = c.location_id
  where a.followups_enabled = true
    and a.published = true
    and c.followup_anchor_at is not null
    and l.private_integration_token is not null
    and c.followups_sent < 3
    and (c.last_inbound_at is null or c.last_inbound_at <= c.followup_anchor_at);
$$;
