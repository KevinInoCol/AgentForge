// Cliente del Backend-AgentForge (FastAPI).
import { supabase } from "@/lib/supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Agent = {
  id: string;
  location_id: string;
  name: string;
  system_prompt: string;
  model: string;
  temperature: number;
  enabled: boolean;
  published: boolean;
  tools: string[];
  created_at: string;
  updated_at: string;
};

export type AgentInput = {
  name: string;
  system_prompt: string;
  model: string;
  temperature: number;
  enabled: boolean;
  tools: string[];
};

// Llamada autenticada: adjunta el access token de Supabase en cada request.
async function req(path: string, init: RequestInit = {}) {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Error ${res.status}`);
  }
  return res.json();
}

// ── Workspaces (tenant, uno por usuario) ────────────────────────
export type Workspace = {
  id: string;
  name?: string;
  has_openai_key: boolean;
  default_model: string;
  has_pit: boolean;
  ghl_location_id?: string | null;
  ghl_connected: boolean;
};

export async function getMyWorkspace(): Promise<Workspace> {
  return req(`/api/workspaces/me`);
}

export async function getWorkspace(id: string): Promise<Workspace> {
  return req(`/api/workspaces/${id}`);
}

export async function saveOpenAISettings(workspaceId: string, input: { openai_api_key?: string; default_model?: string }) {
  return req(`/api/workspaces/${workspaceId}/openai`, { method: "POST", body: JSON.stringify(input) }) as Promise<Workspace>;
}

export async function testGHL(ghl_location_id: string, private_integration_token: string) {
  return req(`/api/workspaces/ghl/test`, {
    method: "POST",
    body: JSON.stringify({ ghl_location_id, private_integration_token }),
  }) as Promise<{ ok: boolean; detail?: string }>;
}

export async function connectGHL(workspaceId: string, ghl_location_id: string, private_integration_token: string) {
  return req(`/api/workspaces/${workspaceId}/ghl`, {
    method: "POST",
    body: JSON.stringify({ ghl_location_id, private_integration_token }),
  }) as Promise<Workspace>;
}

// ── Agentes ─────────────────────────────────────────────────────
export async function listAgents(workspaceId: string): Promise<{ agents: Agent[] }> {
  return req(`/api/agents?workspace_id=${workspaceId}`);
}

export async function getAgent(id: string): Promise<Agent> {
  return req(`/api/agents/${id}`);
}

export async function createAgent(workspaceId: string, input: AgentInput) {
  return req(`/api/agents`, { method: "POST", body: JSON.stringify({ workspace_id: workspaceId, ...input }) });
}

export async function updateAgent(id: string, input: Partial<AgentInput> & { published?: boolean }) {
  return req(`/api/agents/${id}`, { method: "PUT", body: JSON.stringify(input) });
}

export async function deleteAgent(id: string) {
  return req(`/api/agents/${id}`, { method: "DELETE" });
}

export async function generateAgent(
  name: string,
  description: string,
  workspaceId?: string,
): Promise<{ name: string; system_prompt: string }> {
  return req(`/api/agents/generate`, {
    method: "POST",
    body: JSON.stringify({ name, description, workspace_id: workspaceId }),
  });
}

export type ChatMessage = { role: "user" | "assistant"; content: string };

export async function chatAgent(agentId: string, messages: ChatMessage[]): Promise<{ reply: string }> {
  return req(`/api/agents/${agentId}/chat`, { method: "POST", body: JSON.stringify({ messages }) });
}
