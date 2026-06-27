"use client";
import { useState } from "react";

import { updateAgent, type Agent } from "@/lib/api";

const STEPS = [
  { h: "4 horas", hint: "Primer recordatorio suave." },
  { h: "8 horas", hint: "Segundo recordatorio." },
  { h: "12 horas", hint: "Último intento de recuperación." },
];

export function Remarketing({ agent }: { agent: Agent }) {
  const init = agent.followup_messages ?? [];
  const [enabled, setEnabled] = useState(agent.followups_enabled ?? false);
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
      await updateAgent(agent.id, { followups_enabled: enabled, followup_messages: msgs.map((m) => m.trim()) });
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
        Recupera ventas: si un contacto deja de responder, el agente le envía recordatorios
        automáticos a las <strong>4h</strong>, <strong>8h</strong> y <strong>12h</strong> desde su
        última respuesta. Si el contacto contesta, los seguimientos pendientes se cancelan solos.
      </p>

      <label className="inline" style={{ marginTop: 14 }}>
        <input type="checkbox" style={{ width: "auto" }} checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        Activar seguimientos para este agente
      </label>

      <div style={{ opacity: enabled ? 1 : 0.5, pointerEvents: enabled ? "auto" : "none", marginTop: 8 }}>
        {STEPS.map((s, i) => (
          <div key={s.h}>
            <label>Mensaje a las {s.h} <span className="muted">· {s.hint}</span></label>
            <textarea
              value={msgs[i]}
              onChange={(e) => setMsgAt(i, e.target.value)}
              placeholder={`Ej. ¡Hola! Vi que quedó pendiente tu consulta. ¿Te ayudo a continuar?`}
              style={{ minHeight: 70, fontFamily: "inherit", fontSize: 14 }}
            />
          </div>
        ))}
        <p className="muted" style={{ marginTop: 6, fontSize: 12 }}>
          Deja un mensaje vacío para saltar ese recordatorio. (Meta solo permite enviar dentro de las 24h.)
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
