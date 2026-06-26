-- AgentForge — migración 006: contactos + métricas de interacción.
-- Guarda el nombre del contacto en la conversación y agrega una función que
-- lista los contactos del workspace con su nº de interacciones y última actividad.

alter table agentforge_conversations
  add column if not exists contact_name text;

create or replace function agentforge_workspace_contacts(p_workspace_id uuid)
returns table (
  conversation_id uuid,
  ghl_contact_id  text,
  contact_name    text,
  agent_name      text,
  interactions    int,
  last_at         timestamptz
)
language sql stable as $$
  select
    c.id,
    c.ghl_contact_id,
    c.contact_name,
    a.name,
    count(m.id)::int as interactions,
    max(m.created_at) as last_at
  from agentforge_conversations c
  left join agentforge_agents a   on a.id = c.agent_id
  left join agentforge_messages m on m.conversation_id = c.id
  where c.location_id = p_workspace_id
  group by c.id, c.ghl_contact_id, c.contact_name, a.name
  order by max(m.created_at) desc nulls last;
$$;
