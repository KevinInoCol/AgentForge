import type { AgentInput } from "@/lib/api";

// Borrador temporal que pasa del modal "Create Assistant" al form /agents/new.
const KEY = "agentforge:draft";

export function setDraft(draft: Partial<AgentInput>) {
  sessionStorage.setItem(KEY, JSON.stringify(draft));
}

export function takeDraft(): Partial<AgentInput> | null {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  sessionStorage.removeItem(KEY); // un solo uso
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
