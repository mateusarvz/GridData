/**
 * Service for fetching LangChain-accessible schema structure from the backend.
 *
 * This service communicates with the /agente-ia endpoints that return ONLY
 * structural metadata (table names, columns, types, FK relationships) — never
 * row data. Actual row data is only accessed at query time by the SQL Agent.
 */

const API_URL = import.meta.env.VITE_API_URL || '';
const BASE = `${API_URL}/api/v1/agente-ia`;

function getHeaders(): HeadersInit {
  const token = localStorage.getItem('damabox_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface ColunaSchema {
  nome: string;
  tipo: string;
  nullable: boolean;
}

export interface RelacionamentoInfo {
  coluna_local: string;
  referencia: string;
}

export interface TabelaSchema {
  nome_tabela: string;
  origem_arquivo: string | null;
  tipo_arquivo: string | null;
  total_linhas: number;
  criado_em: string | null;
  colunas: ColunaSchema[];
  relacionamento: RelacionamentoInfo | null;
}

export interface EstruturaAcessivelResponse {
  tabelas: TabelaSchema[];
}

export interface ContextoAgenteResponse {
  contexto: string;
  total_tabelas: number;
}

/**
 * Fetch the full structural schema for the authenticated user.
 * Returns ONLY metadata — no row data.
 */
export async function fetchEstruturaAcessivel(): Promise<EstruturaAcessivelResponse> {
  const res = await fetch(`${BASE}/estrutura-acessivel`, {
    method: 'GET',
    headers: getHeaders(),
    signal: AbortSignal.timeout(15000),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Erro ao buscar estrutura de tabelas.');
  }

  return await res.json();
}

/**
 * Fetch the DDL-like text context for the SQL Agent prompt.
 * Useful for debugging and preview.
 */
export async function fetchContextoAgente(): Promise<ContextoAgenteResponse> {
  const res = await fetch(`${BASE}/contexto-agente`, {
    method: 'GET',
    headers: getHeaders(),
    signal: AbortSignal.timeout(15000),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Erro ao buscar contexto do agente.');
  }

  return await res.json();
}

export interface ChatRequest {
  pergunta: string;
}

export interface ChatResponse {
  resposta: string;
}

/**
 * Send a natural language question to the Gemini chat endpoint.
 * The backend generates SQL, queries Supabase, and returns a text response.
 */
export async function sendChatMessage(pergunta: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ pergunta } satisfies ChatRequest),
    signal: AbortSignal.timeout(60000),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Erro ao enviar mensagem para o chat.');
  }

  return await res.json();
}
