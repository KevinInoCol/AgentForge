"use client";
import { useRef, useState } from "react";

import { chatAgent, type ChatMessage } from "@/lib/api";

export function ChatLab({ agentId }: { agentId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [turns, setTurns] = useState(0);
  const endRef = useRef<HTMLDivElement>(null);

  function scroll() {
    setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setLoading(true);
    setError(null);
    scroll();
    try {
      const { reply } = await chatAgent(agentId, next);
      setMessages([...next, { role: "assistant", content: reply }]);
      setTurns((t) => t + 1);
      scroll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al chatear");
      setMessages(messages); // revierte el mensaje del usuario si falló
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chatlab">
      <div className="chatlab-head">
        <span className="muted">{turns} turno(s) · prueba la versión guardada del agente</span>
        <button className="btn secondary" onClick={() => { setMessages([]); setTurns(0); setError(null); }}>
          Limpiar
        </button>
      </div>

      <div className="chatlab-msgs">
        {messages.length === 0 && !loading && (
          <div className="chatlab-empty">Envía un mensaje para empezar.</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>{m.content}</div>
        ))}
        {loading && <div className="bubble assistant">…</div>}
        <div ref={endRef} />
      </div>

      {error && <div className="error" style={{ margin: "0 12px" }}>{error}</div>}

      <div className="chatlab-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Envía un mensaje…"
          disabled={loading}
        />
        <button className="btn" onClick={send} disabled={loading || !input.trim()}>➤</button>
      </div>
    </div>
  );
}
