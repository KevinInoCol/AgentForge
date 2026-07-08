"use client";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import {
  connectGHL,
  deleteConnection,
  getConnections,
  getWorkspace,
  startGoogleConnect,
  testGHL,
  type Connection,
} from "@/lib/api";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

export default function CredentialsPage() {
  const workspaceId = useWorkspaceId();

  const [locationId, setLocationId] = useState("");
  const [pit, setPit] = useState("");
  const [connected, setConnected] = useState(false);

  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  // Conexiones (tools con OAuth: Google Calendar, etc.)
  const [connections, setConnections] = useState<Connection[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [connMsg, setConnMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    getWorkspace(workspaceId)
      .then((w) => {
        setConnected(w.ghl_connected);
        if (w.ghl_location_id) setLocationId(w.ghl_location_id);
      })
      .catch(() => {});
    loadConnections();
  }, [workspaceId]);

  // Al volver del OAuth de Google (?google=connected|error).
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("google");
    if (p === "connected") setConnMsg({ type: "ok", text: "✅ Google Calendar conectado." });
    else if (p === "error") setConnMsg({ type: "error", text: "❌ No se pudo conectar Google Calendar. Intenta de nuevo." });
    if (p) window.history.replaceState({}, "", "/credentials");
  }, []);

  function loadConnections() {
    if (!workspaceId) return;
    getConnections(workspaceId).then((r) => setConnections(r.connections)).catch(() => {});
  }

  const googleConn = connections.find((c) => c.provider === "google_calendar");

  async function handleConnectGoogle() {
    if (!workspaceId) return setConnMsg({ type: "error", text: "Inicializando workspace…" });
    setConnecting(true);
    setConnMsg(null);
    try {
      const { url } = await startGoogleConnect(workspaceId);
      window.location.href = url; // redirige al consent de Google
    } catch (e) {
      setConnMsg({ type: "error", text: e instanceof Error ? e.message : "Error" });
      setConnecting(false);
    }
  }

  async function handleDisconnectGoogle() {
    if (!googleConn) return;
    if (!confirm("¿Desconectar Google Calendar? Los agentes dejarán de poder agendar.")) return;
    try {
      await deleteConnection(googleConn.id);
      setConnMsg({ type: "ok", text: "Google Calendar desconectado." });
      loadConnections();
    } catch (e) {
      setConnMsg({ type: "error", text: e instanceof Error ? e.message : "Error" });
    }
  }

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

      <div className="page-head" style={{ marginTop: 40 }}>
        <h1>Conexiones</h1>
      </div>
      <p className="muted" style={{ maxWidth: 620 }}>
        Conecta servicios externos para darle <strong>herramientas</strong> a tus agentes.
        Una vez conectado, activa la herramienta en el agente que quieras (pestaña del agente).
      </p>

      {connMsg && (
        <div className={connMsg.type === "ok" ? "pill on" : "error"} style={{ marginTop: 12, display: "block", padding: "10px 12px", maxWidth: 620 }}>
          {connMsg.text}
        </div>
      )}

      <div className="panel" style={{ padding: 20, marginTop: 16, maxWidth: 620 }}>
        <div className="inline" style={{ justifyContent: "space-between", width: "100%" }}>
          <div>
            <strong>📅 Google Calendar</strong>
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
              {googleConn
                ? `Conectado${googleConn.account_email ? ` como ${googleConn.account_email}` : ""}.`
                : "Permite al agente consultar disponibilidad y agendar citas."}
            </div>
          </div>
          {googleConn ? (
            <button className="btn secondary" onClick={handleDisconnectGoogle}>Desconectar</button>
          ) : (
            <button className="btn" onClick={handleConnectGoogle} disabled={connecting}>
              {connecting ? "Redirigiendo…" : "Conectar"}
            </button>
          )}
        </div>
      </div>
    </AppShell>
  );
}
