"use client";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { analyzeConversation, getUnresponded, type UnrespondedContact } from "@/lib/api";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

export default function AnalisisPage() {
  const workspaceId = useWorkspaceId();
  const [contacts, setContacts] = useState<UnrespondedContact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    getUnresponded(workspaceId)
      .then((r) => setContacts(r.contacts))
      .catch((e) => setError(e instanceof Error ? e.message : "Error"))
      .finally(() => setLoading(false));
  }, [workspaceId]);

  async function analyze(c: UnrespondedContact) {
    if (!workspaceId) return;
    setBusy(c.conversation_id);
    try {
      const a = await analyzeConversation(workspaceId, c.conversation_id);
      setContacts((prev) => prev.map((x) =>
        x.conversation_id === c.conversation_id
          ? { ...x, analysis_reason: a.reason, analysis_objection: a.objection, analysis_recommendation: a.recommendation, analyzed_at: new Date().toISOString() }
          : x,
      ));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al analizar");
    } finally {
      setBusy(null);
    }
  }

  return (
    <AppShell active="analisis">
      <div className="page-head"><h1>Análisis de Conversaciones</h1></div>
      <p className="muted" style={{ maxWidth: 660 }}>
        Inteligencia de ventas: por qué los contactos que <strong>no respondieron</strong> no
        avanzaron con la compra. El análisis se genera automáticamente con el Agente de Seguimiento
        IA, o puedes pedirlo manualmente. <span className="muted">(Analizar consume tokens de tu OpenAI.)</span>
      </p>

      {error && <div className="error">{error}</div>}
      {loading && <p className="muted">Cargando…</p>}
      {!loading && contacts.length === 0 && (
        <div className="panel"><div className="empty">Aún no hay contactos sin respuesta. Cuando alguien deje una conversación a medias, aparecerá aquí.</div></div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 8 }}>
        {contacts.map((c) => {
          const analyzed = !!c.analysis_reason;
          return (
            <div key={c.conversation_id} className="panel" style={{ padding: 18 }}>
              <div className="row">
                <div>
                  <strong>👤 {c.contact_name || c.ghl_contact_id.slice(0, 10) + "…"}</strong>
                  <div className="muted" style={{ fontSize: 12 }}>
                    Agente: {c.agent_name || "—"} · Última actividad: {c.last_at ? new Date(c.last_at).toLocaleString("es") : "—"}
                  </div>
                </div>
                <button className="btn secondary" onClick={() => analyze(c)} disabled={busy === c.conversation_id}>
                  {busy === c.conversation_id ? "Analizando…" : analyzed ? "Re-analizar" : "Analizar"}
                </button>
              </div>

              {analyzed ? (
                <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 8 }}>
                  <div><strong>🔍 Por qué no avanzó:</strong> <span className="muted">{c.analysis_reason}</span></div>
                  <div><strong>🚧 Objeción / duda:</strong> <span className="muted">{c.analysis_objection}</span></div>
                  <div><strong>💡 Recomendación:</strong> <span className="muted">{c.analysis_recommendation}</span></div>
                </div>
              ) : (
                <div className="muted" style={{ marginTop: 10, fontSize: 13 }}>
                  Sin analizar aún. Pulsa <strong>Analizar</strong> para que la IA evalúe esta conversación.
                </div>
              )}
            </div>
          );
        })}
      </div>
    </AppShell>
  );
}
