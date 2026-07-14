-- ============================================================================
-- MIGRATION: SCHEMA ANALYSIS STAGING TABLES
-- ============================================================================
-- Tabelas temporárias para suporte ao fluxo de inferência de schema via Gemini.
-- Dados são staging: removidos após commit ou expiração (expira_em).
-- NÃO alterar tabelas existentes.
-- ============================================================================

-- ============================================================================
-- 1. SCHEMA_ANALYSIS_SESSIONS - Sessão de análise (agrupa arquivos)
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_analysis_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status VARCHAR(50) DEFAULT 'aguardando_analise',
  -- aguardando_analise | analisado | revisado | confirmado | cancelado
  total_arquivos INT DEFAULT 0,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  expira_em TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),
  CONSTRAINT status_valido CHECK (
    status IN ('aguardando_analise', 'analisado', 'revisado', 'confirmado', 'cancelado')
  )
);

-- ============================================================================
-- 2. SCHEMA_ANALYSIS_TABLES - Schema de cada arquivo dentro da sessão
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_analysis_tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES schema_analysis_sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  nome_arquivo VARCHAR(255) NOT NULL,
  nome_tabela_sugerido VARCHAR(255) NOT NULL,
  -- [{nome, tipo_bruto, tipo_sugerido, nulo_permitido, editado_pelo_usuario}]
  colunas_schema JSONB NOT NULL DEFAULT '[]',
  total_linhas INT DEFAULT 0,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 3. SCHEMA_ANALYSIS_RELATIONSHIPS - Relacionamentos sugeridos/editados
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_analysis_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES schema_analysis_sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tabela_origem_id UUID NOT NULL REFERENCES schema_analysis_tables(id) ON DELETE CASCADE,
  coluna_origem VARCHAR(255) NOT NULL,
  tabela_destino_id UUID NOT NULL REFERENCES schema_analysis_tables(id) ON DELETE CASCADE,
  coluna_destino VARCHAR(255) NOT NULL,
  tipo_relacionamento VARCHAR(50) DEFAULT '1:N',
  grau_confianca DECIMAL(3, 2) DEFAULT 1.0,
  -- 'gemini' ou 'usuario'
  origem VARCHAR(20) DEFAULT 'gemini',
  aprovado BOOLEAN DEFAULT true,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT tipo_relacionamento_valido CHECK (
    tipo_relacionamento IN ('1:1', '1:N', 'N:N')
  ),
  CONSTRAINT origem_valida CHECK (
    origem IN ('gemini', 'usuario')
  ),
  CONSTRAINT grau_confianca_range CHECK (
    grau_confianca >= 0.0 AND grau_confianca <= 1.0
  )
);

-- ============================================================================
-- 4. ROW LEVEL SECURITY
-- ============================================================================
ALTER TABLE schema_analysis_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_analysis_tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_analysis_relationships ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Usuário vê apenas suas sessões de análise" ON schema_analysis_sessions
  FOR ALL USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

CREATE POLICY "Usuário vê apenas suas tabelas de análise" ON schema_analysis_tables
  FOR ALL USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

CREATE POLICY "Usuário vê apenas seus relacionamentos de análise" ON schema_analysis_relationships
  FOR ALL USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

-- ============================================================================
-- 5. INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_sas_user_id ON schema_analysis_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sas_status ON schema_analysis_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sas_expira_em ON schema_analysis_sessions(expira_em);
CREATE INDEX IF NOT EXISTS idx_sat_session_id ON schema_analysis_tables(session_id);
CREATE INDEX IF NOT EXISTS idx_sat_user_id ON schema_analysis_tables(user_id);
CREATE INDEX IF NOT EXISTS idx_sar_session_id ON schema_analysis_relationships(session_id);
CREATE INDEX IF NOT EXISTS idx_sar_user_id ON schema_analysis_relationships(user_id);

-- ============================================================================
-- 6. COMENTÁRIOS
-- ============================================================================
COMMENT ON TABLE schema_analysis_sessions IS 'Sessões temporárias de análise de schema - expiram em 24h';
COMMENT ON TABLE schema_analysis_tables IS 'Metadados de schema dos arquivos carregados na sessão (staging)';
COMMENT ON TABLE schema_analysis_relationships IS 'Relacionamentos sugeridos pelo Gemini ou criados manualmente (staging)';
COMMENT ON COLUMN schema_analysis_tables.colunas_schema IS
  'JSONB: [{nome, tipo_bruto, tipo_sugerido, nulo_permitido, editado_pelo_usuario}]';
COMMENT ON COLUMN schema_analysis_relationships.grau_confianca IS
  'Grau de confiança do Gemini na sugestão de relacionamento (0.0 a 1.0)';
