# Desplegar el Backend en EasyPanel (DigitalOcean) desde GitHub

El backend ya trae `Dockerfile` y `.dockerignore`, así que EasyPanel lo construye solo.

---

## 1. Subir el backend a GitHub

Si `Backend-AgentForge` aún no está en un repo:

```bash
cd Backend-AgentForge
git init
git add .
git commit -m "AgentForge backend"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/agentforge-backend.git
git push -u origin main
```

> El `.env` NO se sube (está en `.dockerignore` y `.gitignore`). Las credenciales se ponen en EasyPanel.

---

## 2. Crear la app en EasyPanel

1. En tu proyecto de EasyPanel → **+ Service → App**.
2. **Source:** GitHub → elige el repo `agentforge-backend` (branch `main`).
3. **Build:** *Dockerfile* (EasyPanel lo detecta automáticamente).
4. **Port:** `8080` (el que expone el contenedor).
5. Deploy.

EasyPanel te dará un **dominio con HTTPS** (ej. `https://agentforge-backend.tu-server.easypanel.host`) o puedes asignar el tuyo.

---

## 3. Variables de entorno (en EasyPanel → Environment)

```env
SUPABASE_URL=https://pajhjpzydkkpmjdofqqp.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...     # la SECRET (no la publishable)
OPENAI_API_KEY=                              # vacía — cada cliente pone la suya
GHL_API_VERSION=2021-04-15
APP_ENV=production

# Debounce: opción simple (sin Redis) para arrancar
BUFFER_ENABLED=false
```

> Tras editar env vars, **redeploy** la app.

---

## 4. (Opcional) Redis para el debounce completo

Si quieres concatenar mensajes seguidos (debounce real):

1. EasyPanel → **+ Service → Template → Redis** (un clic).
2. Copia su host interno (ej. `redis://nombre-redis:6379`).
3. En la app, setea:
   ```env
   BUFFER_ENABLED=true
   REDIS_URL=redis://nombre-redis:6379
   ```
4. Redeploy.

---

## 5. Verificar

```
https://TU-DOMINIO/health      → {"status":"ok"}
https://TU-DOMINIO/docs        → la API
```

---

## 6. Conectar el frontend (Vercel) al backend

1. En Vercel (proyecto `agentforge`) → Settings → Environment Variables:
   ```
   NEXT_PUBLIC_API_URL = https://TU-DOMINIO
   ```
2. Redeploy el frontend (`vercel deploy --prod`), o desde el dashboard.

Ahora el frontend desplegado (https://agentforge-psi.vercel.app) ya habla con el backend → los 4 usuarios pueden usar TODO (login, crear agentes, Chat Lab).

---

## 7. Responder mensajes reales de GHL (FB/IG/WhatsApp)

En la sub-cuenta de HighLevel, crea un **Workflow**:
- **Trigger:** *Customer Replied*.
- **Action → Webhook (POST)** a `https://TU-DOMINIO/webhooks/ghl/inbound` con body:
  ```json
  {
    "locationId": "{{location.id}}",
    "contactId": "{{contact.id}}",
    "message": "{{message.body}}",
    "messageType": "{{message.type}}"
  }
  ```

Requisitos en AgentForge para esa sub-cuenta:
- **Credenciales HighLevel** conectadas (PIT) → para responder.
- **OpenAI key** + un agente **Publicado**.
