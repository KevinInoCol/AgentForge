# Frontend-AgentForge

Panel de creación/gestión de agentes de texto. **Se embebe dentro de GoHighLevel**
vía *Custom Menu Link* (iframe), por lo que el cliente nunca sale de GHL.

Stack: Next.js (App Router) + TypeScript + Supabase JS. Deploy en Vercel.

## Responsabilidad
- Crear/editar agentes (nombre, system prompt, modelo, temperatura, tools, on/off).
- Subir documentos al knowledge base.
- Ver conversaciones, transcripts y métricas de uso.
- NO contiene lógica de inferencia: solo habla con `Backend-AgentForge` (API) y con Supabase.

## Estructura
```
src/
├── app/            ← rutas (App Router)
│   ├── layout.tsx
│   ├── page.tsx            (dashboard)
│   └── agents/            (crear/editar agentes)
├── components/     ← UI reutilizable
└── lib/            ← clientes (api.ts, supabase.ts)
```

## Arranque
```bash
npm install
cp .env.local.example .env.local   # completar
npm run dev
```

## Embeber en GHL
En el Marketplace App → *Custom Menu Link* apuntando a la URL de Vercel.
GHL pasa el contexto (locationId) por query param / SSO para saber qué tenant es.
