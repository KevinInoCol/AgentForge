"use client";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { connectGHL, getWorkspace, testGHL } from "@/lib/api";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

export default function CredentialsPage() {
  const workspaceId = useWorkspaceId();

  const [locationId, setLocationId] = useState("");
  const [pit, setPit] = useState("");
  const [connected, setConnected] = useState(false);

  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    getWorkspace(workspaceId)
      .then((w) => {
        setConnected(w.ghl_connected);
        if (w.ghl_location_id) setLocationId(w.ghl_location_id);
      })
      .catch(() => {});
  }, [workspaceId]);

  async function handleTest() {
    if (!locationId || !pit) return setMsg({ type: "error", text: "Completa LocationID y PIT." });
    setTesting(true);
    setMsg(null);
    try {
      const r = await testGHL(locationId.trim(), pit.trim());
      setMsg(r.ok
        ? { type: "ok", text: "✅ Conexión válida con HighLevel." }
        : { type: "error", text: `❌ No se pudo conectar: ${r.detail ?? "revisa el PIT"}` });
    } catch (e) {
      setMsg({ type: "error", text: e instanceof Error ? e.message : "Error" });
    } finally {
      setTesting(false);
    }
  }

  async function handleConnect() {
    if (!workspaceId) return setMsg({ type: "error", text: "Inicializando workspace…" });
    if (!locationId || !pit) return setMsg({ type: "error", text: "Completa LocationID y PIT." });
    setSaving(true);
    setMsg(null);
    try {
      const w = await connectGHL(workspaceId, locationId.trim(), pit.trim());
      setConnected(w.ghl_connected);
      setPit("");
      setMsg({ type: "ok", text: "✅ HighLevel conectado. Tus agentes publicados ya pueden recibir mensajes." });
    } catch (e) {
      setMsg({ type: "error", text: e instanceof Error ? e.message : "Error al conectar" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell active="credentials">
      <div className="page-head">
        <h1>Credenciales de HighLevel</h1>
        {connected && <span className="pill on">Conectado</span>}
      </div>

      <p className="muted" style={{ maxWidth: 620 }}>
        Esto es el paso de <strong>go-live</strong>: conecta tu sub-cuenta para que los agentes
        <strong> publicados</strong> reciban mensajes reales. No hace falta para construir ni probar
        (eso solo necesita tu OpenAI key en Ajustes). Genera el PIT en GHL: Settings → Private
        Integrations (permisos de Conversations, Contacts, Locations).
      </p>

      <div className="panel" style={{ padding: 20, marginTop: 16 }}>
        <label>Location ID</label>
        <input value={locationId} onChange={(e) => setLocationId(e.target.value)} placeholder="Ej. cmqd...qk8q" />

        <label>Private Integration Token (PIT)</label>
        <input type="password" value={pit} onChange={(e) => setPit(e.target.value)}
          placeholder={connected ? "•••••••• (ya guardado — escribe uno nuevo para reemplazar)" : "pit-xxxxxxxx"} />

        {msg && <div className={msg.type === "ok" ? "pill on" : "error"} style={{ marginTop: 14, display: "block", padding: "10px 12px" }}>{msg.text}</div>}

        <div className="inline" style={{ marginTop: 20 }}>
          <button className="btn secondary" onClick={handleTest} disabled={testing}>
            {testing ? "Probando…" : "Probar conexión"}
          </button>
          <button className="btn" onClick={handleConnect} disabled={saving}>
            {saving ? "Conectando…" : "Conectar HighLevel"}
          </button>
        </div>
      </div>
    </AppShell>
  );
}
