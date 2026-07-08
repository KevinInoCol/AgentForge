"use client";
import { useEffect, useState } from "react";

import { getToolsCatalog, type AgentInput, type ToolSpec } from "@/lib/api";

const DEFAULT_PROMPT = `<Identidad>
Eres {bot_name}, el asistente de texto del negocio.
</Identidad>
<Personalidad>
Cercano, claro y resolutivo. Respondes en mensajes cortos (es un chat).
</Personalidad>
<Rol>
Atender por texto: responder dudas y, cuando aplique, agendar o derivar a un humano.
</Rol>
<Instrucciones_Generales>
- No inventes datos; si no sabes, ofrece derivar a un humano.
</Instrucciones_Generales>`;

const MODELS = ["gpt-4.1", "gpt-4.1-mini", "gpt-4o"];

export function AgentForm({
  initial,
  submitLabel,
  onSubmit,
}: {
  initial?: Partial<AgentInput>;
  submitLabel: string;
  onSubmit: (values: AgentInput) => Promise<void>;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [systemPrompt, setSystemPrompt] = useState(initial?.system_prompt ?? DEFAULT_PROMPT);
  const [model, setModel] = useState(initial?.model ?? "gpt-4.1");
  const [temperature, setTemperature] = useState(initial?.temperature ?? 0);
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);
  const [tools, setTools] = useState<string[]>(initial?.tools ?? []);
  const [catalog, setCatalog] = useState<ToolSpec[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getToolsCatalog().then((r) => setCatalog(r.tools)).catch(() => {});
  }, []);

  function toggleTool(key: string) {
    setTools((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ name, system_prompt: systemPrompt, model, temperature, enabled, tools });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <label>Nombre del agente</label>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej. Asistente de Ventas" required />

      <label>System prompt</label>
      <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} required />

      <div className="row" style={{ gap: 16 }}>
        <div style={{ flex: 1 }}>
          <label>Modelo</label>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <label>Temperatura ({temperature})</label>
          <input
            type="range" min={0} max={1} step={0.1}
            value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
          />
        </div>
      </div>

      <label className="inline" style={{ marginTop: 18 }}>
        <input
          type="checkbox" style={{ width: "auto" }}
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        Agente activo (responde mensajes)
      </label>

      {catalog.length > 0 && (
        <div style={{ marginTop: 22 }}>
          <label>Herramientas</label>
          <p className="muted" style={{ fontSize: 13, marginTop: 2, marginBottom: 10 }}>
            Las que requieren conexión (ej. Google Calendar) solo funcionan si la conectaste en
            <strong> Credenciales</strong>. La Base de Conocimiento se activa sola al subir documentos.
          </p>
          {catalog.map((t) => (
            <label key={t.key} className="inline" style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
              <input
                type="checkbox" style={{ width: "auto", marginTop: 3 }}
                checked={tools.includes(t.key)}
                onChange={() => toggleTool(t.key)}
              />
              <span>
                <strong>{t.label}</strong>
                {t.provider && <span className="muted" style={{ fontSize: 12 }}> · requiere conexión</span>}
                <br />
                <span className="muted" style={{ fontSize: 12 }}>{t.description}</span>
              </span>
            </label>
          ))}
        </div>
      )}

      {error && <div className="error">{error}</div>}

      <div style={{ marginTop: 24 }} className="inline">
        <button className="btn" type="submit" disabled={saving}>
          {saving ? "Guardando…" : submitLabel}
        </button>
        <a className="btn secondary" href="/">Cancelar</a>
      </div>
    </form>
  );
}
