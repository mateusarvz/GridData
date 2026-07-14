// Tipos para a feature de análise de schema

export interface ColunaSchema {
  nome: string;
  tipo_bruto: string;
  tipo_sugerido: string;
  nulo_permitido: boolean;
  editado_pelo_usuario: boolean;
}

export interface TabelaUploadada {
  table_id: string;
  nome_arquivo: string;
  nome_tabela_sugerido: string;
  total_linhas: number;
  colunas: ColunaSchema[];
}

export interface Relacionamento {
  id?: string;
  tabela_origem_id: string;
  coluna_origem: string;
  tabela_destino_id: string;
  coluna_destino: string;
  tipo_relacionamento: '1:1' | '1:N' | 'N:N';
  grau_confianca: number;
  origem: 'gemini' | 'usuario';
  aprovado: boolean;
  nome_tabela_origem: string;
  nome_tabela_destino: string;
}

export interface SessaoAnalise {
  session_id: string;
  status: string;
  total_arquivos: number;
  tabelas: TabelaUploadada[];
  relacionamentos: Relacionamento[];
}

// Tipos Postgres válidos para o seletor
export const POSTGRES_TYPES = [
  'VARCHAR(255)',
  'VARCHAR(100)',
  'VARCHAR(50)',
  'TEXT',
  'INT',
  'BIGINT',
  'SMALLINT',
  'DECIMAL(10,2)',
  'DECIMAL(18,6)',
  'NUMERIC',
  'BOOLEAN',
  'DATE',
  'TIMESTAMP WITH TIME ZONE',
  'TIMESTAMP',
  'UUID',
  'JSONB',
  'JSON',
  'FLOAT',
  'DOUBLE PRECISION',
] as const;

export type PostgresType = (typeof POSTGRES_TYPES)[number];

export const TIPO_RELACIONAMENTO_OPTIONS: Array<'1:1' | '1:N' | 'N:N'> = ['1:1', '1:N', 'N:N'];
