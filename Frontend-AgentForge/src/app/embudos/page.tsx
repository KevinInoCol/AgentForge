"use client";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { getPipelines, getRoutes, listAgents, saveRoutes, type Agent, type Pipeline } from "@/lib/api";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

export default function EmbudosPage() {
  const workspaceId = useWorkspaceId();
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [assign, setAssign] = useState<Record<string, string>>({}); // stage_id -> agent_id
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    (async () => {
      try {
        const [p, r, a] = await Promise.all([
          getPipelines(workspaceId),
          getRoutes(workspaceId),
          listAgents(workspaceId),
        ]);
        setPipelines(p.pipelines);
        setAgents(a.agents);
        if (p.pipelines[0]) setSelected(p.pipelines[0].id);
        // precargar asignaciones
        const map: Record<string, string> = {};
        r.routes.forEach((x) => { if (x.agent_id) map[x.stage_id] = x.agent_id; });
        setAssign(map);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error");
      } finally {
        setLoading(false);
      }
    })();
  }, [workspaceId]);

  const pipeline = useMemo(() => pipelines.find((p) => p.id === selected), [pipelines, selected]);

  async function save() {
    if (!workspaceId || !pipeline) return;
    setSaving(true);
    setMsg(null);
    try {
      const routes = pipeline.stages.map((s) => ({ stage_id: s.id, agent_id: assign[s.id] || null }));
      await saveRoutes(workspaceId, pipeline.id, routes);
      setMsg("✅ Embudo guardado. Cada etapa enrutará al agente asignado.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell active="embudos">
      <div className="page-head"><h1>Embudos</h1></div>
      <p className="muted" style={{ maxWidth: 660 }}>
        Asigna un agente a cada etapa de tu embudo de ventas. Cuando un contacto escriba, responderá
        el agente de la etapa donde está su oportunidad en GoHighLevel. Las etapas sin agente usan el
        agente publicado por defecto.
      </p>

      {loading && <p className="muted">Cargando embudos…</p>}
      {error && (
        <div className="error">
          {error.includes("Conecta") ? error : `No se pudieron cargar los embudos: ${error}`}
        </div>
      )}

      {!loading && !error && pipelines.length === 0 && (
        <div className="panel"><div className="empty">No se encontraron pipelines en tu sub-cuenta de GHL.</div></div>
      )}

      {!loading && pipeline && (
        <>
          <div style={{ maxWidth: 360, marginTop: 8 }}>
            <label>Pipeline</label>
            <select value={selected} onChange={(e) => setSelected(e.target.value)}>
              {pipelines.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <div className="panel" style={{ marginTop: 16 }}>
            <table>
              <thead><tr><th>Etapa</th><th>Agente asignado</th></tr></thead>
              <tbody>
                {pipeline.stages.sort((a, b) => a.position - b.position).map((s) => (
                  <tr key={s.id}>
                    <td><strong>{s.name}</strong></td>
                    <td>
                      <select
                        value={assign[s.id] || ""}
                        onChange={(e) => setAssign((prev) => ({ ...prev, [s.id]: e.target.value }))}
                        style={{ maxWidth: 320 }}
                      >
                        <option value="">— Sin agente (usa el por defecto) —</option>
                        {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {msg && <div className="pill on" style={{ display: "block", padding: "10px 12px", marginTop: 14 }}>{msg}</div>}

          <div style={{ marginTop: 16 }}>
            <button className="btn" onClick={save} disabled={saving}>{saving ? "Guardando…" : "Guardar embudo"}</button>
          </div>
        </>
      )}
    </AppShell>
  );
}
