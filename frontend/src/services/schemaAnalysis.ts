import type { SessaoAnalise, TabelaUploadada, Relacionamento } from '../types/schemaAnalysis';
import { useUserStore } from '../store/userStore';

const BASE = '/api/v1/schema-analysis';

function getUserId(): string {
  const { userId } = useUserStore.getState();
  if (!userId) throw new Error('Usuário não autenticado.');
  return userId;
}

// ---------------------------------------------------------------------------
// 1. Criar sessão e fazer upload de arquivos
// ---------------------------------------------------------------------------
export async function criarSessaoAnalise(files: FileList): Promise<{
  session_id: string;
  tabelas: TabelaUploadada[];
}> {
  const user_id = getUserId();
  const formData = new FormData();
  formData.append('user_id', user_id);
  for (const file of Array.from(files)) {
    formData.append('files', file);
  }

  const res = await fetch(`${BASE}/sessions`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Erro ao criar sessão de análise.');
  }

  const data = await res.json();
  return { session_id: data.session_id, tabelas: data.tabelas };
}

// ---------------------------------------------------------------------------
// 2. Inferir schema via Gemini
// ---------------------------------------------------------------------------
export async function inferirSchema(session_id: string): Promise<SessaoAnalise> {
  const user_id = getUserId();

  const res = await fetch(`${BASE}/sessions/${session_id}/infer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Erro ao inferir schema.');
  }

  const data = await res.json();
  return {
    session_id: data.session_id,
    status: 'analisado',
    total_arquivos: data.tabelas?.length ?? 0,
    tabelas: data.tabelas ?? [],
    relacionamentos: data.relacionamentos ?? [],
  };
}

// ---------------------------------------------------------------------------
// 3. Buscar sessão completa
// ---------------------------------------------------------------------------
export async function getSessao(session_id: string): Promise<SessaoAnalise> {
  const user_id = getUserId();

  const res = await fetch(`${BASE}/sessions/${session_id}?user_id=${encodeURIComponent(user_id)}`);

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Sessão não encontrada.');
  }

  const data = await res.json();
  return {
    session_id: data.session_id,
    status: data.status,
    total_arquivos: data.total_arquivos,
    tabelas: data.tabelas ?? [],
    relacionamentos: data.relacionamentos ?? [],
  };
}

// ---------------------------------------------------------------------------
// 4. Editar tipo de coluna
// ---------------------------------------------------------------------------
export async function editarColuna(
  session_id: string,
  table_id: string,
  column_name: string,
  novo_tipo: string
): Promise<void> {
  const user_id = getUserId();

  const res = await fetch(
    `${BASE}/sessions/${session_id}/tables/${table_id}/columns/${encodeURIComponent(column_name)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id, novo_tipo }),
    }
  );

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Erro ao editar coluna.');
  }
}

// ---------------------------------------------------------------------------
// 5. Criar relacionamento manual
// ---------------------------------------------------------------------------
export async function criarRelacionamento(
  session_id: string,
  payload: Omit<Relacionamento, 'id' | 'aprovado' | 'grau_confianca' | 'origem' | 'nome_tabela_origem' | 'nome_tabela_destino' | 'justificativa'>
): Promise<Relacionamento> {
  const user_id = getUserId();

  const res = await fetch(`${BASE}/sessions/${session_id}/relationships`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id, ...payload }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Erro ao criar relacionamento.');
  }

  const data = await res.json();
  return data.relacionamento;
}

// ---------------------------------------------------------------------------
// 6. Editar relacionamento (aprovar/reprovar/alterar tipo)
// ---------------------------------------------------------------------------
export async function editarRelacionamento(
  session_id: string,
  relationship_id: string,
  patch: { aprovado?: boolean; tipo_relacionamento?: string }
): Promise<void> {
  const user_id = getUserId();

  const res = await fetch(`${BASE}/sessions/${session_id}/relationships/${relationship_id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id, ...patch }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Erro ao editar relacionamento.');
  }
}

// ---------------------------------------------------------------------------
// 7. Commit — gerar DDL e inserir no Supabase
// ---------------------------------------------------------------------------
export async function commitSessao(session_id: string): Promise<{
  sql_gerado: string;
  tabelas_criadas: string[];
}> {
  const user_id = getUserId();

  const res = await fetch(`${BASE}/sessions/${session_id}/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Erro ao confirmar schema.');
  }

  const data = await res.json();
  return { sql_gerado: data.sql_gerado, tabelas_criadas: data.tabelas_criadas ?? [] };
}
