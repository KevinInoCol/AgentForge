"use client";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { getContacts, type Contact } from "@/lib/api";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

function fmt(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es", { dateStyle: "medium", timeStyle: "short" });
}

export default function ContactsPage() {
  const workspaceId = useWorkspaceId();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [totals, setTotals] = useState({ contacts: 0, interactions: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    getContacts(workspaceId)
      .then((r) => {
        setContacts(r.contacts);
        setTotals({ contacts: r.total_contacts, interactions: r.total_interactions });
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Error"))
      .finally(() => setLoading(false));
  }, [workspaceId]);

  return (
    <AppShell active="contacts">
      <div className="page-head">
        <h1>Contactos</h1>
      </div>
      <p className="muted">Personas con las que tus agentes han conversado.</p>

      {/* Métricas */}
      <div style={{ display: "flex", gap: 16, marginTop: 8, flexWrap: "wrap" }}>
        <div className="panel" style={{ padding: "16px 22px", minWidth: 180 }}>
          <div className="muted" style={{ fontSize: 12 }}>Total contactos</div>
          <div style={{ fontSize: 28, fontWeight: 800 }}>{totals.contacts}</div>
        </div>
        <div className="panel" style={{ padding: "16px 22px", minWidth: 180 }}>
          <div className="muted" style={{ fontSize: 12 }}>Total interacciones</div>
          <div style={{ fontSize: 28, fontWeight: 800 }}>{totals.interactions}</div>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="panel" style={{ marginTop: 16 }}>
        <table>
          <thead>
            <tr>
              <th>Contacto</th>
              <th>Agente</th>
              <th>Interacciones</th>
              <th>Última actividad</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={4} className="empty">Cargando…</td></tr>}
            {!loading && contacts.length === 0 && (
              <tr><td colSpan={4} className="empty">Aún no hay conversaciones. Cuando un contacto le escriba a tu agente, aparecerá aquí.</td></tr>
            )}
            {contacts.map((c) => (
              <tr key={c.conversation_id}>
                <td>
                  <div className="name-cell">
                    👤 {c.contact_name || <span className="id-mono">{c.ghl_contact_id.slice(0, 10)}…</span>}
                  </div>
                </td>
                <td className="muted">{c.agent_name || "—"}</td>
                <td><strong>{c.interactions}</strong></td>
                <td className="muted">{fmt(c.last_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
