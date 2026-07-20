const API_URL = import.meta.env.VITE_API_URL || '';
const BASE_URL = `${API_URL}/api/v1/gemini`;
const TOKEN_KEY = 'damabox_token';

export interface GeminiStatus {
  connected: boolean;
  error?: string | null;
}

export interface GeminiChatResult {
  response: string;
  error?: string | null;
}

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem(TOKEN_KEY);
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function getGeminiStatus(): Promise<GeminiStatus> {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    return { connected: false, error: 'Token ausente. Login precisa salvar damabox_token.' };
  }

  const res = await fetch(`${BASE_URL}/status`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    if (res.status === 401) {
      return { connected: false, error: '401: token ausente ou expirado. Login precisa salvar damabox_token.' };
    }
    return { connected: false, error: `HTTP ${res.status}` };
  }
  return res.json();
}

export async function sendGeminiChat(prompt: string): Promise<GeminiChatResult> {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    return { response: '', error: 'Token ausente. Faça login novamente.' };
  }

  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    if (res.status === 401) {
      return { response: '', error: '401: token ausente ou expirado. Login precisa salvar damabox_token.' };
    }
    return { response: '', error: `HTTP ${res.status}` };
  }
  return res.json();
}
