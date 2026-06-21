"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/AppShell";
import { AgentForm } from "@/components/AgentForm";
import { createAgent, type AgentInput } from "@/lib/api";
import { takeDraft } from "@/lib/draft";
import { useWorkspaceId } from "@/lib/useWorkspaceId";

export default function NewAgent() {
  const workspaceId = useWorkspaceId();
  const router = useRouter();
  const [initial, setInitial] = useState<Partial<AgentInput> | undefined>(undefined);
  const [ready, setReady] = useState(false);

  // El borrador viene del modal "Crear asistente" (plantilla / IA / import).
  useEffect(() => {
    setInitial(takeDraft() ?? undefined);
    setReady(true);
  }, []);

  if (!ready) return null;

  return (
    <AppShell active="assistants">
      <p className="muted"><a href="/">← Asistentes</a></p>
      <h1>Crear asistente</h1>
      <div className="form-wrap">
        <AgentForm
          initial={initial}
          submitLabel="Crear asistente"
          onSubmit={async (values) => {
            if (!workspaceId) throw new Error("Inicializando workspace… intenta de nuevo.");
            const created = await createAgent(workspaceId, values);
            router.push(`/agents/${created.id}`); // cae directo en el editor
          }}
        />
      </div>
    </AppShell>
  );
}
