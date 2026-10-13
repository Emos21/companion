// Companion API client.
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8099";

export type Decision = {
  action: "auto" | "escalate";
  severity: "none" | "low" | "high" | "critical";
  reason: string;
  confidence: number;
  retrieval_score: number;
  matched: string[];
};

export type Source = { id: string; title: string; score: number };

export type ChatResponse = {
  conversation_id: number;
  reply: string;
  escalated: boolean;
  escalation_id?: number;
  decision: Decision;
  confidence: number;
  retrieval_score: number;
  provider: string;
  model: string;
  fell_back: boolean;
  sources: Source[];
};

export type Escalation = {
  id: number;
  conversation_id: number;
  user_message: string;
  severity: Decision["severity"];
  reason: string;
  matched: string[];
  draft_answer: string | null;
  sources: Source[];
  provider: string;
  status: "open" | "resolved";
  created_at: number;
  resolved_reply: string | null;
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Request failed (${res.status})`);
  return res.json();
}

export function sendChat(message: string, conversationId: number | null) {
  return post<ChatResponse>("/chat", { message, conversation_id: conversationId });
}

export async function listEscalations(): Promise<Escalation[]> {
  const res = await fetch(`${BASE}/escalations`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()).escalations;
}

export function resolveEscalation(id: number, reply: string) {
  return post(`/escalations/${id}/resolve`, { reply });
}

export type ConvMessage = { role: string; content: string; at: number };

export async function getConversationMessages(id: number): Promise<ConvMessage[]> {
  const res = await fetch(`${BASE}/conversations/${id}/messages`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()).messages;
}
