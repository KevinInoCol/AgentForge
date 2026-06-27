-- AgentForge — migración 010: Análisis de Conversaciones.
-- Guarda el análisis de por qué el contacto no avanzó + función para listarlos.

alter table agentforge_conversations
  add column if not exists analysis_reason text,
  add column if not exists analysis_objection text,
  add column if not exists analysis_recommendation text,
  add column if not exists analyzed_at timestamptz;

-- Contactos que NO respondieron (el agente habló último y el lead quedó en silencio),
-- con su análisis si existe.
create or replace function agentforge_unresponded(p_workspace_id uuid)
returns table (
  conversation_id uuid,
  ghl_contact_id  text,
  contact_name    text,
  agent_name      text,
  last_at         timestamptz,
  analysis_reason text,
  analysis_objection text,
  analysis_recommendation text,
  analyzed_at     timestamptz
)
language sql stable as $$
  select
    c.id, c.ghl_contact_id, c.contact_name, a.name, c.followup_anchor_at,
    c.analysis_reason, c.analysis_objection, c.analysis_recommendation, c.analyzed_at
  from agentforge_conversations c
  left join agentforge_agents a on a.id = c.agent_id
  where c.location_id = p_workspace_id
    and c.followup_anchor_at is not null
    and (c.last_inbound_at is null or c.last_inbound_at <= c.followup_anchor_at)
  order by c.followup_anchor_at desc nulls last;
$$;
