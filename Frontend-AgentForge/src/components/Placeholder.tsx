"use client";
import { AppShell } from "@/components/AppShell";

export function Placeholder({ active, title }: { active: string; title: string }) {
  return (
    <AppShell active={active}>
      <div className="page-head">
        <h1>{title}</h1>
      </div>
      <div className="panel">
        <div className="empty">
          <p>🚧 Sección en construcción</p>
          <p className="muted">Esta parte llega en una fase posterior del roadmap.</p>
        </div>
      </div>
    </AppShell>
  );
}
