const API_URL = import.meta.env.VITE_API_URL || '';
const BASE_URL = `${API_URL}/api/v1/gemini`;

export interface GeminiStatus {
  connected: boolean;
  error?: string | null;
}

export interface GeminiChatResult {
  response: string;
  error?: string | null;
}

export async function getGeminiStatus(): Promise<GeminiStatus> {
  const res = await fetch(`${BASE_URL}/status`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    return { connected: false, error: `HTTP ${res.status}` };
  }
  return res.json();
}

export async function sendGeminiChat(prompt: string): Promise<GeminiChatResult> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    return { response: '', error: `HTTP ${res.status}` };
  }
  return res.json();
}
