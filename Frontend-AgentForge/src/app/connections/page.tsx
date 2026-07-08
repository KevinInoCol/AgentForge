"use client";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import {
  deleteConnection,
  getConnections,
  startGoogleConnect,
  type Connection,
} from "@/lib/api";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

export default function ConnectionsPage() {
  const workspaceId = useWorkspaceId();

  const [connections, setConnections] = useState<Connection[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadConnections();
  }, [workspaceId]);

  // Al volver del OAuth de Google (?google=connected|error).
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("google");
    if (p === "connected") setMsg({ type: "ok", text: "✅ Google Calendar conectado." });
    else if (p === "error") setMsg({ type: "error", text: "❌ No se pudo conectar Google Calendar. Intenta de nuevo." });
    if (p) window.history.replaceState({}, "", "/connections");
  }, []);

  function loadConnections() {
    if (!workspaceId) return;
    getConnections(workspaceId).then((r) => setConnections(r.connections)).catch(() => {});
  }

  const googleConn = connections.find((c) => c.provider === "google_calendar");

  async function handleConnectGoogle() {
    if (!workspaceId) return setMsg({ type: "error", text: "Inicializando workspace…" });
    setConnecting(true);
    setMsg(null);
    try {
      const { url } = await startGoogleConnect(workspaceId);
      window.location.href = url; // redirige al consent de Google
    } catch (e) {
      setMsg({ type: "error", text: e instanceof Error ? e.message : "Error" });
      setConnecting(false);
    }
  }

  async function handleDisconnectGoogle() {
    if (!googleConn) return;
    if (!confirm("¿Desconectar Google Calendar? Los agentes dejarán de poder agendar.")) return;
    try {
      await deleteConnection(googleConn.id);
      setMsg({ type: "ok", text: "Google Calendar desconectado." });
      loadConnections();
    } catch (e) {
      setMsg({ type: "error", text: e instanceof Error ? e.message : "Error" });
    }
  }

  return (
    <AppShell active="connections">
      <div className="page-head">
        <h1>Conexiones</h1>
      </div>
      <p className="muted" style={{ maxWidth: 620 }}>
        Conecta servicios externos para darle <strong>herramientas</strong> a tus agentes. Una vez
        conectado, activa la herramienta en el agente que quieras (en la pestaña del agente).
      </p>

      {msg && (
        <div className={msg.type === "ok" ? "pill on" : "error"} style={{ marginTop: 12, display: "block", padding: "10px 12px", maxWidth: 620 }}>
          {msg.text}
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
