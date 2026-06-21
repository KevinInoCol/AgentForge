-- AgentForge — migración 005: búsqueda por similitud en la base de conocimiento.
-- Función RPC que devuelve los fragmentos más parecidos a un embedding, por agente.
-- Se llama desde el backend con supabase.rpc('match_agentforge_chunks', {...}).

create or replace function match_agentforge_chunks(
  p_agent_id uuid,
  p_query_embedding vector(1536),
  p_match_count int default 5
)
returns table (id uuid, content text, similarity float)
language sql stable
as $$
  select
    c.id,
    c.content,
    1 - (c.embedding <=> p_query_embedding) as similarity
  from agentforge_knowledge_chunks c
  where c.agent_id = p_agent_id
  order by c.embedding <=> p_query_embedding
  limit p_match_count;
$$;
