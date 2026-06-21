-- AgentForge — migración 002: API key de OpenAI + modelo por defecto por sub-cuenta.
-- Corre esto si ya ejecutaste 001_init.sql antes (es idempotente).

alter table agentforge_locations
  add column if not exists openai_api_key text,
  add column if not exists default_model text default 'gpt-4.1';
