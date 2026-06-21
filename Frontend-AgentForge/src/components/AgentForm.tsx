"use client";
import { useState } from "react";

import type { AgentInput } from "@/lib/api";

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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ name, system_prompt: systemPrompt, model, temperature, enabled, tools: [] });
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
