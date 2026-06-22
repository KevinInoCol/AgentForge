"use client";
import { useEffect, useRef, useState } from "react";

import { deleteKnowledge, listKnowledge, uploadKnowledge, type KnowledgeDoc } from "@/lib/api";

export function KnowledgeBase({ agentId }: { agentId: string }) {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    try {
      const r = await listKnowledge(agentId);
      setDocs(r.documents);
    } catch (e) {
      setMsg({ type: "error", text: e instanceof Error ? e.message : "Error" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [agentId]);

  async function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setMsg(null);
    try {
      const r = await uploadKnowledge(agentId, file);
      setMsg({ type: "ok", text: `✅ "${r.filename}" indexado (${r.chunks} fragmentos).` });
      await refresh();
    } catch (err) {
      setMsg({ type: "error", text: err instanceof Error ? err.message : "Error al subir" });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onDelete(doc: KnowledgeDoc) {
    if (!confirm(`¿Eliminar "${doc.filename}" de la base de conocimiento?`)) return;
    await deleteKnowledge(agentId, doc.id);
    setDocs((prev) => prev.filter((d) => d.id !== doc.id));
  }

  return (
    <div>
      <p className="muted" style={{ maxWidth: 620 }}>
        Sube documentos (PDF o TXT) con la info del negocio: catálogo, precios, servicios,
        políticas, FAQs. El agente los consultará con la herramienta <strong>Base de Conocimiento</strong>
        cuando el usuario pregunte algo específico.
      </p>

      <div className="inline" style={{ marginTop: 8 }}>
        <input ref={fileRef} type="file" accept=".pdf,.txt" onChange={onPick} disabled={uploading} style={{ width: "auto" }} />
        {uploading && <span className="muted">Procesando e indexando…</span>}
      </div>

      {msg && (
        <div className={msg.type === "ok" ? "pill on" : "error"} style={{ marginTop: 14, display: "block", padding: "10px 12px" }}>
          {msg.text}
        </div>
      )}

      <div className="panel" style={{ marginTop: 16 }}>
        <table>
          <thead>
            <tr><th>Documento</th><th>Subido</th><th></th></tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={3} className="empty">Cargando…</td></tr>}
            {!loading && docs.length === 0 && (
              <tr><td colSpan={3} className="empty">Aún no hay documentos. Sube el primero.</td></tr>
            )}
            {docs.map((d) => (
              <tr key={d.id}>
                <td>📄 {d.filename}</td>
                <td className="muted">{new Date(d.created_at).toLocaleDateString("es")}</td>
                <td><div className="actions"><button className="icon-btn danger" onClick={() => onDelete(d)} title="Eliminar">🗑</button></div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
