# Usuarios y autenticación (Supabase Auth)

Pasos para habilitar el login y crear los usuarios de prueba.

---

## 1. Migración 004 en Supabase (SQL Editor)

Agrega el dueño del workspace (aislamiento por usuario). Es idempotente.

```sql
-- 004: dueño del workspace (Supabase Auth)
alter table agentforge_locations
  add column if not exists owner_user_id uuid;

create index if not exists agentforge_locations_owner_idx
  on agentforge_locations (owner_user_id);
```

---

## 2. Variables del frontend (`Frontend-AgentForge/.env.local`)

El frontend necesita Supabase para el login:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_...   # la PUBLISHABLE/anon (pública), NO la secret
```

> Misma URL de Supabase que el backend. Tras editar, reinicia `npm run dev`.

---

## 3. Crear los usuarios

Desde `Backend-AgentForge`, con el env activo:

```bash
conda activate ARIA-AgentForge
python scripts/create_users.py correo1 pass1 correo2 pass2 correo3 pass3
```

- Crea los usuarios vía la admin API de Supabase, ya **confirmados** (pueden loguear de inmediato).
- Requiere `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` en `.env` (ya configuradas).

Ejemplo:
```bash
python scripts/create_users.py \
  ana@ariaia.com Clave123! \
  luis@ariaia.com Clave123! \
  maria@ariaia.com Clave123!
```

> También puedes crearlos a mano en Supabase → Authentication → Users → Add user
> (marca "Auto Confirm User").

---

## 4. Cómo entran

1. Abren el frontend → los redirige a **`/login`**.
2. Ingresan su correo + contraseña.
3. Cada uno obtiene su **propio workspace** (ve solo sus agentes).
4. Primer paso dentro: **🧠 Credenciales OpenAI** → pegar su API key → crear/probar agentes.

---

## Notas

- **Solo login** (no hay registro público). Los usuarios se crean aquí.
- Cada usuario está **aislado**: sus agentes/credenciales no los ve nadie más.
- Los workspaces creados antes del login quedaron con `owner_user_id = NULL`
  (huérfanos) y no aparecen para nadie. Para limpiarlos:
  ```sql
  delete from agentforge_locations where owner_user_id is null;
  ```
