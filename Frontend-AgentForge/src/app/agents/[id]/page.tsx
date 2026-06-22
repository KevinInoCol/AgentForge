"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import { ChatLab } from "@/components/ChatLab";
import { KnowledgeBase } from "@/components/KnowledgeBase";
import { generateAgent, getAgent, getWorkspace, updateAgent, type Agent } from "@/lib/api";

const TABS = ["Builder", "Chat Lab", "Knowledge Lab"] as const;
const SUB = ["Global Prompt", "Greeting", "Fields & Values"] as const;
const TOOLKIT = [
  "Chat Settings",
  "Tools & APIs",
  "Map Custom Fields",
  "Knowledge Base",
  "Calendars",
  "Find & Replace",
] as const;
const MODELS = ["gpt-4.1", "gpt-4.1-mini", "gpt-4o"];

export default function EditAgent({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [error, setError] = useState<string | null>(null);

  // estado editable
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("gpt-4.1");
  const [temperature, setTemperature] = useState(0);
  const [enabled, setEnabled] = useState(true);

  const [tab, setTab] = useState<(typeof TABS)[number]>("Builder");
  const [sub, setSub] = useState<(typeof SUB)[number]>("Global Prompt");
  const [openTool, setOpenTool] = useState<string | null>("Chat Settings");
  const [published, setPublished] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    getAgent(id)
      .then((a) => {
        setAgent(a);
        setName(a.name);
        setPrompt(a.system_prompt);
        setModel(a.model);
        setTemperature(a.temperature);
        setEnabled(a.enabled);
        setPublished(a.published);
      })
      .catch((e) => setError(e.message));
  }, [id]);

  function mark<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setDirty(true);
    };
  }

  async function persist(opts: { setPublished?: boolean } = {}) {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const patch: Record<string, unknown> = { name, system_prompt: prompt, model, temperature, enabled };
      if (opts.setPublished === true) {
        patch.enabled = true;
        patch.published = true;
      } else if (opts.setPublished === false) {
        patch.published = false;
      }
      await updateAgent(id, patch);
      setDirty(false);
      if (opts.setPublished === true) {
        setEnabled(true);
        setPublished(true);
        const ws = agent ? await getWorkspace(agent.location_id).catch(() => null) : null;
        setNotice(
          ws?.ghl_connected
            ? "✅ Publicado y en vivo. Ya recibe mensajes reales."
            : "✅ Publicado. Conecta HighLevel en 🔑 Credenciales para que reciba mensajes reales.",
        );
      } else if (opts.setPublished === false) {
        setPublished(false);
        setNotice("⏸ Despublicado. El agente ya no responde mensajes reales.");
      } else {
        setNotice("✅ Guardado. El Chat Lab ya usa esta versión.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  async function regenerate() {
    const desc = window.prompt("Describe el objetivo del asistente y la IA reescribirá el prompt:");
    if (!desc) return;
    setGenerating(true);
    try {
      const draft = await generateAgent(name, desc);
      setPrompt(draft.system_prompt);
      setDirty(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al generar");
    } finally {
      setGenerating(false);
    }
  }

  if (error && !agent) {
    return <AppShell active="assistants"><div className="error">{error}</div></AppShell>;
  }
  if (!agent) {
    return <AppShell active="assistants"><p className="muted">Cargando…</p></AppShell>;
  }

  return (
    <AppShell active="assistants">
      <div className="editor-top">
        <div className="editor-title">
          <a className="muted" href="/" title="Volver">←</a>
          <div>
            <input value={name} onChange={(e) => mark(setName)(e.target.value)} />
            <div className="id-mono" style={{ padding: "0 6px", cursor: "pointer" }}
              onClick={() => navigator.clipboard?.writeText(agent.id)} title="Copiar ID">
              ID: {agent.id.slice(0, 8)}… ⧉
            </div>
          </div>
        </div>
        <div className="inline">
          <span className={`pill ${published ? "on" : "off"}`}>{published ? "Publicado" : "Borrador"}</span>
          {dirty && <span className="unsaved">● Cambios sin guardar</span>}
          <select className="badge" style={{ width: "auto" }} value={model} onChange={(e) => mark(setModel)(e.target.value)}>
            {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <button className="btn secondary" onClick={() => persist()} disabled={saving || !dirty}>
            {saving ? "Guardando…" : "Guardar"}
          </button>
          {published ? (
            <button className="btn secondary" onClick={() => persist({ setPublished: false })} disabled={saving} title="Sacar de línea: deja de responder mensajes reales">
              Despublicar
            </button>
          ) : (
            <button className="btn" onClick={() => persist({ setPublished: true })} disabled={saving}>
              Publicar
            </button>
          )}
        </div>
      </div>

      {notice && <div className="pill on" style={{ display: "block", padding: "10px 12px", marginBottom: 12 }}>{notice}</div>}

      <div className="editor-tabs">
        {TABS.map((t) => {
          const enabledTab = t === "Builder" || t === "Chat Lab" || t === "Knowledge Lab";
          return (
            <div
              key={t}
              className={`editor-tab ${tab === t ? "active" : ""} ${enabledTab ? "" : "disabled"}`}
              onClick={() => enabledTab && setTab(t)}
            >
              {t}
            </div>
          );
        })}
      </div>

      {error && <div className="error">{error}</div>}

      {tab === "Chat Lab" && <ChatLab agentId={agent.id} />}
      {tab === "Knowledge Lab" && <KnowledgeBase agentId={agent.id} />}

      {tab === "Builder" && (
      <div className="builder">
        {/* Columna principal */}
        <div>
          <div className="sub-toolbar">
            {SUB.map((s) => (
              <span
                key={s}
                className={`sub-link ${sub === s ? "active" : ""}`}
                onClick={() => setSub(s)}
              >
                {s}
              </span>
            ))}
            <span className="sub-link gen" onClick={regenerate}>
              {generating ? "✨ Generando…" : "✨ Generate Prompt"}
            </span>
          </div>

          {sub === "Global Prompt" && (
            <div className="prompt-area">
              <div className="muted" style={{ marginBottom: 6 }}>{prompt.length} / 8024 caracteres</div>
              <textarea value={prompt} onChange={(e) => mark(setPrompt)(e.target.value)} />
            </div>
          )}
          {sub !== "Global Prompt" && (
            <div className="panel"><div className="empty soon">🚧 «{sub}» llega en una fase posterior.</div></div>
          )}
        </div>

        {/* Tool Kit */}
        <div className="toolkit">
          <div className="toolkit-head">Tool Kit</div>
          {TOOLKIT.map((t) => (
            <div key={t}>
              <div className="toolkit-item" onClick={() => setOpenTool(openTool === t ? null : t)}>
                <span>{t}</span>
                <span className="muted">{openTool === t ? "▾" : "›"}</span>
              </div>
              {openTool === t && (
                <div className="toolkit-panel">
                  {t === "Chat Settings" ? (
                    <>
                      <label>Modelo</label>
                      <select value={model} onChange={(e) => mark(setModel)(e.target.value)}>
                        {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
                      </select>
                      <label>Temperatura ({temperature})</label>
                      <input type="range" min={0} max={1} step={0.1} value={temperature}
                        onChange={(e) => mark(setTemperature)(Number(e.target.value))} />
                      <label className="inline" style={{ marginTop: 12 }}>
                        <input type="checkbox" style={{ width: "auto" }} checked={enabled}
                          onChange={(e) => mark(setEnabled)(e.target.checked)} />
                        Agente activo
                      </label>
                    </>
                  ) : (
                    <span className="soon">🚧 Próximamente</span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      )}
    </AppShell>
  );
}
