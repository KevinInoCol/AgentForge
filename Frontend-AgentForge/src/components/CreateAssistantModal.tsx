"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { createAgent, generateAgent, getAgent } from "@/lib/api";
import { setDraft } from "@/lib/draft";
import { TEMPLATES } from "@/lib/templates";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

type Step = "menu" | "template" | "generate" | "import" | "blank";

const EXAMPLE =
  "Asistente para una clínica dental. Atiende a pacientes por WhatsApp, responde dudas sobre tratamientos y precios, y agenda citas confirmando fecha y hora. Si el paciente tiene una urgencia, deriva a un humano.";

export function CreateAssistantModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [step, setStep] = useState<Step>("menu");

  function goNewWith(draft: Parameters<typeof setDraft>[0]) {
    setDraft(draft);
    router.push("/agents/new");
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {step === "menu" && <Menu onPick={setStep} />}
        {step === "template" && <TemplateStep onBack={() => setStep("menu")} onPick={goNewWith} />}
        {step === "generate" && <GenerateStep onBack={() => setStep("menu")} onDone={goNewWith} />}
        {step === "import" && <ImportStep onBack={() => setStep("menu")} onDone={goNewWith} />}
        {step === "blank" && <BlankStep onBack={() => setStep("menu")} />}
      </div>
    </div>
  );
}

function Menu({ onPick }: { onPick: (s: Step) => void }) {
  return (
    <>
      <h2>Crear asistente</h2>
      <p className="muted">¿Cómo quieres crear tu próximo asistente?</p>
      <div className="card-grid">
        <button className="opt-card" disabled style={{ opacity: 0.5, cursor: "not-allowed" }}>
          <div className="opt-ico">🗂️</div>
          <strong>Desde plantilla</strong>
          <span className="muted">Parte de una plantilla afinada (ventas, soporte, agendamiento, e-commerce).</span>
          <span className="plan-tag" style={{ background: "var(--muted)", marginTop: 6 }}>No disponible aún</span>
        </button>
        <button className="opt-card" disabled style={{ opacity: 0.5, cursor: "not-allowed" }}>
          <div className="opt-ico">✨</div>
          <strong>Generar con IA</strong>
          <span className="muted">Describe tu negocio y la IA redacta el asistente por ti.</span>
          <span className="plan-tag" style={{ background: "var(--muted)", marginTop: 6 }}>No disponible aún</span>
        </button>
        <button className="opt-card" disabled style={{ opacity: 0.5, cursor: "not-allowed" }}>
          <div className="opt-ico">📋</div>
          <strong>Importar por ID</strong>
          <span className="muted">Duplica un asistente existente usando su ID.</span>
          <span className="plan-tag" style={{ background: "var(--muted)", marginTop: 6 }}>No disponible aún</span>
        </button>
        <button className="opt-card" onClick={() => onPick("blank")}>
          <div className="opt-ico">⬜</div>
          <strong>Lienzo en blanco</strong>
          <span className="muted">Empieza sin configuración y arma el asistente desde cero.</span>
        </button>
      </div>
    </>
  );
}

function TemplateStep({
  onBack,
  onPick,
}: {
  onBack: () => void;
  onPick: (draft: Parameters<typeof setDraft>[0]) => void;
}) {
  return (
    <>
      <h2>Desde plantilla</h2>
      <p className="muted">Elige un punto de partida. Podrás editarlo todo después.</p>
      <div className="card-grid">
        {TEMPLATES.map((t) => (
          <button key={t.key} className="opt-card" onClick={() => onPick(t.draft)}>
            <strong>{t.label}</strong>
            <span className="muted">{t.description}</span>
          </button>
        ))}
      </div>
      <div className="modal-foot">
        <button className="btn secondary" onClick={onBack}>← Volver</button>
      </div>
    </>
  );
}

function GenerateStep({
  onBack,
  onDone,
}: {
  onBack: () => void;
  onDone: (draft: Parameters<typeof setDraft>[0]) => void;
}) {
  const workspaceId = useWorkspaceId();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    if (!description.trim()) return setError("Escribe una descripción.");
    setLoading(true);
    setError(null);
    try {
      const draft = await generateAgent(name, description, workspaceId ?? undefined);
      onDone({ name: draft.name, system_prompt: draft.system_prompt });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al generar");
      setLoading(false);
    }
  }

  return (
    <>
      <h2>Generar asistente</h2>
      <p className="muted">Danos un nombre y una descripción y redactamos un borrador.</p>

      <div className="row">
        <label style={{ margin: "16px 0 6px" }}>Nombre</label>
        <a className="muted" style={{ cursor: "pointer" }} onClick={() => setDescription(EXAMPLE)}>Usar ejemplo</a>
      </div>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre del asistente" />

      <label>Descripción</label>
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Describe el objetivo del asistente — qué debe hacer, con quién habla y los pasos que debe seguir."
      />

      {error && <div className="error">{error}</div>}

      <div className="modal-foot">
        <button className="btn secondary" onClick={onBack} disabled={loading}>← Volver</button>
        <button className="btn" onClick={handleGenerate} disabled={loading}>
          {loading ? "Generando…" : "Generar asistente"}
        </button>
      </div>
    </>
  );
}

function BlankStep({ onBack }: { onBack: () => void }) {
  const router = useRouter();
  const workspaceId = useWorkspaceId();
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    if (!name.trim()) return setError("Ponle un nombre al asistente.");
    if (!workspaceId) return setError("Inicializando workspace… intenta de nuevo en un momento.");
    setLoading(true);
    setError(null);
    try {
      const created = await createAgent(workspaceId, {
        name: name.trim(),
        system_prompt: `Eres ${name.trim()}, un asistente de IA útil.`,
        model: "gpt-4.1",
        temperature: 0,
        enabled: true,
        tools: [],
      });
      router.push(`/agents/${created.id}`); // cae directo en el editor
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al crear");
      setLoading(false);
    }
  }

  return (
    <>
      <h2>Crear asistente en blanco</h2>
      <p className="muted">Empieza con una hoja limpia y configura todo desde cero.</p>
      <label>Nombre del asistente</label>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Ej. Asistente inmobiliario"
        autoFocus
        onKeyDown={(e) => e.key === "Enter" && handleCreate()}
      />
      {error && <div className="error">{error}</div>}
      <div className="modal-foot">
        <button className="btn secondary" onClick={onBack} disabled={loading}>← Volver</button>
        <button className="btn" onClick={handleCreate} disabled={loading}>
          {loading ? "Creando…" : "Crear asistente"}
        </button>
      </div>
    </>
  );
}

function ImportStep({
  onBack,
  onDone,
}: {
  onBack: () => void;
  onDone: (draft: Parameters<typeof setDraft>[0]) => void;
}) {
  const [id, setId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleImport() {
    if (!id.trim()) return setError("Pega un ID de asistente.");
    setLoading(true);
    setError(null);
    try {
      const a = await getAgent(id.trim());
      onDone({
        name: `${a.name} (copia)`,
        system_prompt: a.system_prompt,
        model: a.model,
        temperature: a.temperature,
        enabled: a.enabled,
        tools: a.tools,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se encontró ese ID");
      setLoading(false);
    }
  }

  return (
    <>
      <h2>Importar por ID</h2>
      <p className="muted">Pega el ID de un asistente para crear una copia en tu cuenta.</p>
      <label>ID del asistente</label>
      <input value={id} onChange={(e) => setId(e.target.value)} placeholder="uuid del asistente" />
      {error && <div className="error">{error}</div>}
      <div className="modal-foot">
        <button className="btn secondary" onClick={onBack} disabled={loading}>← Volver</button>
        <button className="btn" onClick={handleImport} disabled={loading}>
          {loading ? "Importando…" : "Importar"}
        </button>
      </div>
    </>
  );
}
