# Actualizar la base de datos (migraciones 002 + 003)

Si ya corriste la versión **vieja** de `001_init.sql` (cuando `ghl_location_id` era
`NOT NULL` y no existían las columnas de OpenAI ni `published`), corre este bloque
en **Supabase → SQL Editor → New query → Run**.

Es **idempotente**: seguro de correr aunque algunas columnas ya existan.

```sql
-- 002: API key de OpenAI + modelo por defecto por workspace
alter table agentforge_locations
  add column if not exists openai_api_key text,
  add column if not exists default_model text default 'gpt-4.1';

-- 003: desacoplar el workspace de HighLevel + estado de publicación del agente
alter table agentforge_locations alter column ghl_location_id drop not null;

alter table agentforge_agents
  add column if not exists published boolean not null default false;
```

## Verificar que quedó bien

```sql
select column_name, is_nullable
from information_schema.columns
where table_name = 'agentforge_locations'
order by column_name;
```

Debes ver:
- `ghl_location_id` con `is_nullable = YES`
- `openai_api_key` presente
- `default_model` presente

Y en `agentforge_agents` debe existir la columna `published`.

## Después
No hace falta reiniciar el backend (es solo cambio en la BD). Recarga el frontend
y el `POST /api/workspaces` debería responder **200** con un `"id"`.
