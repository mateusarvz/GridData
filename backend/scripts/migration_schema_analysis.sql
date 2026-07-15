-- ============================================================================
-- MIGRATION: SCHEMA ANALYSIS STAGING TABLES (table_schema)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS table_schema;

-- Remove legacy public tables from old flow
DROP TABLE IF EXISTS public.schema_analysis_relationships CASCADE;
DROP TABLE IF EXISTS public.schema_analysis_tables CASCADE;

-- ----------------------------------------------------------------------------
-- 1) Session header
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS table_schema.schema_analysis_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  status VARCHAR(50) DEFAULT 'aguardando_analise',
  total_arquivos INT DEFAULT 0,
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  expira_em TIMESTAMPTZ DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),
  CONSTRAINT status_valido CHECK (
    status IN ('aguardando_analise', 'analisado', 'revisado', 'confirmado', 'cancelado')
  )
);

-- ----------------------------------------------------------------------------
-- 2) Table-level schema metadata
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS table_schema.schema_analysis_tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES table_schema.schema_analysis_sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  nome_arquivo VARCHAR(255) NOT NULL,
  nome_tabela_sugerido VARCHAR(255) NOT NULL,
  colunas_schema JSONB NOT NULL DEFAULT '[]',
  total_linhas INT DEFAULT 0,
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 3) Relationship suggestions/edits
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS table_schema.schema_analysis_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES table_schema.schema_analysis_sessions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tabela_origem_id UUID NOT NULL REFERENCES table_schema.schema_analysis_tables(id) ON DELETE CASCADE,
  coluna_origem VARCHAR(255) NOT NULL,
  tabela_destino_id UUID NOT NULL REFERENCES table_schema.schema_analysis_tables(id) ON DELETE CASCADE,
  coluna_destino VARCHAR(255) NOT NULL,
  tipo_relacionamento VARCHAR(50) DEFAULT '1:N',
  grau_confianca DECIMAL(3, 2) DEFAULT 1.0,
  origem VARCHAR(20) DEFAULT 'gemini',
  aprovado BOOLEAN DEFAULT true,
  justificativa TEXT DEFAULT '',
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT tipo_relacionamento_valido CHECK (tipo_relacionamento IN ('1:1', '1:N', 'N:N')),
  CONSTRAINT origem_valida CHECK (origem IN ('gemini', 'usuario')),
  CONSTRAINT grau_confianca_range CHECK (grau_confianca >= 0.0 AND grau_confianca <= 1.0)
);

-- ----------------------------------------------------------------------------
-- 4) Uploaded row staging (for final SQL insert)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS table_schema.schema_analysis_rows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES table_schema.schema_analysis_sessions(id) ON DELETE CASCADE,
  table_id UUID NOT NULL REFERENCES table_schema.schema_analysis_tables(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  row_index INT NOT NULL,
  row_data JSONB NOT NULL DEFAULT '{}',
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 5) RLS
-- ----------------------------------------------------------------------------
ALTER TABLE table_schema.schema_analysis_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE table_schema.schema_analysis_tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE table_schema.schema_analysis_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE table_schema.schema_analysis_rows ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Usuario ve apenas suas sessoes de analise" ON table_schema.schema_analysis_sessions;
CREATE POLICY "Usuario ve apenas suas sessoes de analise" ON table_schema.schema_analysis_sessions
  FOR ALL USING (user_id = (SELECT id FROM public.users WHERE auth.uid()::text = users.id::text));

DROP POLICY IF EXISTS "Usuario ve apenas suas tabelas de analise" ON table_schema.schema_analysis_tables;
CREATE POLICY "Usuario ve apenas suas tabelas de analise" ON table_schema.schema_analysis_tables
  FOR ALL USING (user_id = (SELECT id FROM public.users WHERE auth.uid()::text = users.id::text));

DROP POLICY IF EXISTS "Usuario ve apenas seus relacionamentos de analise" ON table_schema.schema_analysis_relationships;
CREATE POLICY "Usuario ve apenas seus relacionamentos de analise" ON table_schema.schema_analysis_relationships
  FOR ALL USING (user_id = (SELECT id FROM public.users WHERE auth.uid()::text = users.id::text));

DROP POLICY IF EXISTS "Usuario ve apenas suas linhas de analise" ON table_schema.schema_analysis_rows;
CREATE POLICY "Usuario ve apenas suas linhas de analise" ON table_schema.schema_analysis_rows
  FOR ALL USING (user_id = (SELECT id FROM public.users WHERE auth.uid()::text = users.id::text));

-- ----------------------------------------------------------------------------
-- 6) Indexes
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_sas_user_id ON table_schema.schema_analysis_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sas_status ON table_schema.schema_analysis_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sas_expira_em ON table_schema.schema_analysis_sessions(expira_em);
CREATE INDEX IF NOT EXISTS idx_sat_session_id ON table_schema.schema_analysis_tables(session_id);
CREATE INDEX IF NOT EXISTS idx_sat_user_id ON table_schema.schema_analysis_tables(user_id);
CREATE INDEX IF NOT EXISTS idx_sar_session_id ON table_schema.schema_analysis_relationships(session_id);
CREATE INDEX IF NOT EXISTS idx_sar_user_id ON table_schema.schema_analysis_relationships(user_id);
CREATE INDEX IF NOT EXISTS idx_sar_aprovado ON table_schema.schema_analysis_relationships(aprovado);
CREATE INDEX IF NOT EXISTS idx_sar_table_id ON table_schema.schema_analysis_rows(table_id);
CREATE INDEX IF NOT EXISTS idx_sar_session_user ON table_schema.schema_analysis_rows(session_id, user_id);

-- ----------------------------------------------------------------------------
-- 7) Comments
-- ----------------------------------------------------------------------------
COMMENT ON TABLE table_schema.schema_analysis_sessions IS 'Staging session for schema analysis';
COMMENT ON TABLE table_schema.schema_analysis_tables IS 'Schema metadata per uploaded file';
COMMENT ON TABLE table_schema.schema_analysis_relationships IS 'Suggested and edited relationships';
COMMENT ON TABLE table_schema.schema_analysis_rows IS 'Staging rows used to generate and execute final SQL commit';

-- ----------------------------------------------------------------------------
-- 8) Grants for service_role
-- ----------------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT USAGE ON SCHEMA table_schema TO service_role;

    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE table_schema.schema_analysis_sessions TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE table_schema.schema_analysis_tables TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE table_schema.schema_analysis_relationships TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE table_schema.schema_analysis_rows TO service_role;
  END IF;
END
$$;

-- ----------------------------------------------------------------------------
-- POSTGREST: EXPOSE table_schema TO API
-- ----------------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
    ALTER ROLE authenticator SET pgrst.db_schemas = 'public,table_schema,graphql_public';
    PERFORM pg_notify('pgrst', 'reload config');
    PERFORM pg_notify('pgrst', 'reload schema');
  END IF;
END
$$;
