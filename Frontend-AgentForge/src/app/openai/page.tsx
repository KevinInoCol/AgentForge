"use client";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { getWorkspace, saveOpenAISettings } from "@/lib/api";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

const MODELS = ["gpt-4.1", "gpt-4.1-mini", "gpt-4o"];

export default function OpenAICredentialsPage() {
  const workspaceId = useWorkspaceId();
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("gpt-4.1");
  const [hasKey, setHasKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    getWorkspace(workspaceId)
      .then((w) => {
        setHasKey(w.has_openai_key);
        if (w.default_model) setModel(w.default_model);
      })
      .catch(() => {});
  }, [workspaceId]);

  async function handleSave() {
    if (!workspaceId) return setMsg({ type: "error", text: "Inicializando workspace… intenta de nuevo." });
    setSaving(true);
    setMsg(null);
    try {
      const w = await saveOpenAISettings(workspaceId, {
        openai_api_key: apiKey.trim() || undefined,
        default_model: model,
      });
      setHasKey(w.has_openai_key);
      setApiKey("");
      setMsg({ type: "ok", text: "✅ Credenciales de OpenAI guardadas." });
    } catch (e) {
      setMsg({ type: "error", text: e instanceof Error ? e.message : "Error al guardar" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell active="openai">
      <div className="page-head">
        <h1>Credenciales de OpenAI</h1>
        {hasKey && <span className="pill on">Conectado</span>}
      </div>

      <p className="muted" style={{ maxWidth: 620 }}>
        Pega tu <strong>API key de OpenAI</strong>. Es lo único que necesitas para construir
        y probar tus agentes (Chat Lab, Generar con IA). El consumo de tokens se cobra a
        <strong> tu cuenta de OpenAI</strong>. La consigues en platform.openai.com → API keys.
      </p>

      <div className="panel" style={{ padding: 20, marginTop: 16 }}>
        <label>API key de OpenAI</label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={hasKey ? "•••••••• (ya guardada — escribe una nueva para reemplazar)" : "sk-..."}
        />

        <label>Modelo por defecto</label>
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <p className="muted" style={{ marginTop: 6 }}>
          Modelo inicial al crear un asistente. Cada asistente puede cambiarlo en su editor.
        </p>

        {msg && (
          <div className={msg.type === "ok" ? "pill on" : "error"} style={{ marginTop: 14, display: "block", padding: "10px 12px" }}>
            {msg.text}
          </div>
        )}

        <div style={{ marginTop: 20 }}>
          <button className="btn" onClick={handleSave} disabled={saving}>
            {saving ? "Guardando…" : "Guardar credenciales"}
          </button>
        </div>
      </div>
    </AppShell>
  );
}
