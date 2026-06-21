"use client";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { CreateAssistantModal } from "@/components/CreateAssistantModal";
import { deleteAgent, listAgents, type Agent } from "@/lib/api";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

const TABS = ["Todos", "Favoritos", "Importados", "Archivados"] as const;

function fmtDate(iso: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es", { month: "short", day: "numeric", year: "numeric" });
}

export default function AssistantsPage() {
  const workspaceId = useWorkspaceId();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<(typeof TABS)[number]>("Todos");
  const [showCreate, setShowCreate] = useState(false);

  async function refresh(id: string) {
    setLoading(true);
    try {
      const r = await listAgents(id);
      setAgents(r.agents);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (workspaceId) refresh(workspaceId);
  }, [workspaceId]);

  const filtered = useMemo(
    () => agents.filter((a) => a.name.toLowerCase().includes(query.toLowerCase())),
    [agents, query],
  );

  async function handleDelete(a: Agent) {
    if (!confirm(`¿Eliminar el asistente "${a.name}"?`)) return;
    await deleteAgent(a.id);
    setAgents((prev) => prev.filter((x) => x.id !== a.id));
  }

  if (workspaceId === null) {
    return (
      <AppShell active="assistants">
        <div className="error">No se pudo inicializar el workspace. ¿El backend está corriendo?</div>
      </AppShell>
    );
  }

  return (
    <AppShell active="assistants">
      <div className="page-head">
        <h1>Asistentes</h1>
        <div className="inline">
          <a className="btn secondary" href="#">📁 Crear carpeta</a>
          <button className="btn" onClick={() => setShowCreate(true)}>+ Crear asistente</button>
        </div>
      </div>

      {showCreate && <CreateAssistantModal onClose={() => setShowCreate(false)} />}

      <div className="tabs">
        {TABS.map((t) => (
          <div key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t}
            <span className="count">{t === "Todos" ? agents.length : 0}</span>
          </div>
        ))}
      </div>

      <div className="toolbar">
        <div className="search">
          <span className="ico">🔍</span>
          <input placeholder="Buscar un asistente…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Modelo</th>
              <th>Actualizado</th>
              <th>Creado</th>
              <th>ID</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} className="empty">Cargando…</td></tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr><td colSpan={6} className="empty">
                {tab === "Todos" ? "Aún no hay asistentes. Crea el primero." : "Nada por aquí."}
              </td></tr>
            )}
            {!loading && tab === "Todos" && filtered.map((a) => (
              <tr key={a.id}>
                <td>
                  <div className="name-cell">
                    <span className={`dot ${a.published ? "" : "off"}`} />
                    {a.name}
                    <span className={`pill ${a.published ? "on" : "off"}`} style={{ marginLeft: 8 }}>
                      {a.published ? "Publicado" : "Borrador"}
                    </span>
                  </div>
                </td>
                <td className="muted">{a.model}</td>
                <td className="muted">{fmtDate(a.updated_at)}</td>
                <td className="muted">{fmtDate(a.created_at)}</td>
                <td className="id-mono">{a.id.slice(0, 8)}</td>
                <td>
                  <div className="actions">
                    <a className="icon-btn" href={`/agents/${a.id}`} title="Editar">✏️</a>
                    <button className="icon-btn danger" onClick={() => handleDelete(a)} title="Eliminar">🗑</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  );
}
