"use client";
import { useState } from "react";

import { updateAgent, type Agent } from "@/lib/api";

const STEPS = [
  { h: "4 horas", hint: "Primer recordatorio suave." },
  { h: "8 horas", hint: "Segundo recordatorio." },
  { h: "12 horas", hint: "Último intento de recuperación." },
];

type Mode = "fixed" | "ai";

export function Remarketing({ agent }: { agent: Agent }) {
  const init = agent.followup_messages ?? [];
  const [enabled, setEnabled] = useState(agent.followups_enabled ?? false);
  const [mode, setMode] = useState<Mode>(agent.followup_mode ?? "fixed");
  const [msgs, setMsgs] = useState<string[]>([init[0] || "", init[1] || "", init[2] || ""]);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  function setMsgAt(i: number, v: string) {
    setMsgs((prev) => prev.map((m, idx) => (idx === i ? v : m)));
  }

  async function save() {
    setSaving(true);
    setMsg(null);
    try {
      await updateAgent(agent.id, {
        followups_enabled: enabled,
        followup_mode: mode,
        followup_messages: msgs.map((m) => m.trim()),
      });
      setMsg({ type: "ok", text: "✅ Seguimientos guardados." });
    } catch (e) {
      setMsg({ type: "error", text: e instanceof Error ? e.message : "Error al guardar" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="form-wrap">
      <h2 style={{ fontSize: 16, margin: "0 0 4px" }}>Seguimiento y Remarketing</h2>
      <p className="muted" style={{ maxWidth: 640 }}>
        Recupera ventas: si un contacto deja de responder, se le envían recordatorios automáticos a las
        <strong> 4h</strong>, <strong>8h</strong> y <strong>12h</strong> desde su última respuesta.
        Si el contacto contesta, los pendientes se cancelan solos.
      </p>

      <label className="inline" style={{ marginTop: 14 }}>
        <input type="checkbox" style={{ width: "auto" }} checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        Activar seguimientos para este agente
      </label>

      <div style={{ opacity: enabled ? 1 : 0.5, pointerEvents: enabled ? "auto" : "none", marginTop: 12 }}>
        {/* Selector de modo */}
        <div className="card-grid" style={{ marginTop: 4 }}>
          <button
            type="button"
            className="opt-card"
            onClick={() => setMode("fixed")}
            style={mode === "fixed" ? { borderColor: "var(--accent-2)", background: "var(--hover)" } : {}}
          >
            <div className="opt-ico">📝</div>
            <strong>Mensajes fijos</strong>
            <span className="muted">Tú escribes los 3 mensajes. <strong>No consume tokens.</strong></span>
          </button>
          <button
            type="button"
            className="opt-card"
            onClick={() => setMode("ai")}
            style={mode === "ai" ? { borderColor: "var(--accent-2)", background: "var(--hover)" } : {}}
          >
            <div className="opt-ico">🤖</div>
            <strong>Agente de Seguimiento (IA)</strong>
            <span className="muted">Analiza la conversación y redacta un mensaje persuasivo. <strong>Consume tokens.</strong></span>
          </button>
        </div>

        {mode === "fixed" && (
          <div style={{ marginTop: 14 }}>
            {STEPS.map((s, i) => (
              <div key={s.h}>
                <label>Mensaje a las {s.h} <span className="muted">· {s.hint}</span></label>
                <textarea
                  value={msgs[i]}
                  onChange={(e) => setMsgAt(i, e.target.value)}
                  placeholder="Ej. ¡Hola! Vi que quedó pendiente tu consulta. ¿Te ayudo a continuar?"
                  style={{ minHeight: 70, fontFamily: "inherit", fontSize: 14 }}
                />
              </div>
            ))}
            <p className="muted" style={{ marginTop: 6, fontSize: 12 }}>
              Deja un mensaje vacío para saltar ese recordatorio.
            </p>
          </div>
        )}

        {mode === "ai" && (
          <div className="panel" style={{ padding: 16, marginTop: 14 }}>
            <p style={{ margin: 0, fontSize: 14 }}>
              🤖 En cada recordatorio (4h, 8h, 12h), un <strong>Agente de Seguimiento</strong> leerá la
              conversación, detectará por qué el contacto no avanzó y le escribirá un mensaje personalizado
              y persuasivo para recuperar la venta.
            </p>
            <p className="muted" style={{ marginTop: 10, fontSize: 13 }}>
              ⚠️ <strong>Consume tokens de tu cuenta de OpenAI</strong> cada vez que analiza y genera un
              mensaje (se cobra a tu key). Solo se ejecuta cuando hay un seguimiento que enviar.
            </p>
          </div>
        )}

        <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>
          Meta solo permite enviar dentro de las 24h del último mensaje del contacto.
        </p>
      </div>

      {msg && (
        <div className={msg.type === "ok" ? "pill on" : "error"} style={{ marginTop: 14, display: "block", padding: "10px 12px" }}>
          {msg.text}
        </div>
      )}

      <div style={{ marginTop: 18 }}>
        <button className="btn" onClick={save} disabled={saving}>{saving ? "Guardando…" : "Guardar seguimientos"}</button>
      </div>
    </div>
  );
}
