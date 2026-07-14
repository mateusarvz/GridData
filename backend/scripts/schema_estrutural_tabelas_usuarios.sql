-- ============================================================================
-- SCHEMA ESTRUTURAL PARA TABELAS DE USUÁRIOS
-- ============================================================================
-- Este schema armazena a estrutura de tabelas, colunas e relacionamentos
-- criados pelos usuários do sistema em um segundo banco de dados.
-- Cada tabela e relacionamento pertence a um usuário identificado pelo UUID
-- do usuário no banco principal de autenticação/usuários.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- 1. USER TABLES - Tabelas criadas pelos usuários
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  user_email VARCHAR(255),
  user_nome_usuario VARCHAR(255),
  nome_tabela VARCHAR(255) NOT NULL,
  descricao TEXT,
  origem VARCHAR(255),
  tipo_arquivo VARCHAR(50),
  total_linhas INT DEFAULT 0,
  tamanho_mb DECIMAL(10, 2) DEFAULT 0,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP WITH TIME ZONE,
  ativo BOOLEAN DEFAULT true,
  UNIQUE(user_id, nome_tabela),
  CONSTRAINT nome_tabela_valido CHECK (nome_tabela ~ '^[a-zA-Z_][a-zA-Z0-9_]*$')
);

-- ============================================================================
-- 2. USER TABLE COLUMNS - Metadados das colunas das tabelas do usuário
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_table_columns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_table_id UUID NOT NULL REFERENCES user_tables(id) ON DELETE CASCADE,
  nome_coluna VARCHAR(255) NOT NULL,
  tipo_dado VARCHAR(50) NOT NULL,
  tamanho INT,
  permite_nulo BOOLEAN DEFAULT true,
  chave_primaria BOOLEAN DEFAULT false,
  chave_unica BOOLEAN DEFAULT false,
  indice INT,
  ordem_coluna INT DEFAULT 0,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_table_id, nome_coluna),
  CONSTRAINT nome_coluna_valido CHECK (nome_coluna ~ '^[a-zA-Z_][a-zA-Z0-9_]*$')
);

-- ============================================================================
-- 3. USER TABLE RELATIONSHIPS - Relacionamentos entre tabelas do usuário
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_table_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  tabela_origem_id UUID NOT NULL REFERENCES user_tables(id) ON DELETE CASCADE,
  coluna_origem_id UUID NOT NULL REFERENCES user_table_columns(id) ON DELETE CASCADE,
  tabela_destino_id UUID NOT NULL REFERENCES user_tables(id) ON DELETE CASCADE,
  coluna_destino_id UUID NOT NULL REFERENCES user_table_columns(id) ON DELETE CASCADE,
  tipo_relacionamento VARCHAR(50) DEFAULT '1:N',
  nome_relacionamento VARCHAR(255),
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(tabela_origem_id, coluna_origem_id, tabela_destino_id, coluna_destino_id)
);

-- ============================================================================
-- 4. USER TABLE DATA - Dados de tabela em formato JSON (opcional)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_table_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_table_id UUID NOT NULL REFERENCES user_tables(id) ON DELETE CASCADE,
  linha_numero INT NOT NULL,
  dados JSONB NOT NULL,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_table_id, linha_numero)
);

-- ============================================================================
-- 5. PERMISSIONS - Controle de edição e acesso por usuário
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_table_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_table_id UUID NOT NULL REFERENCES user_tables(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  pode_editar BOOLEAN DEFAULT false,
  pode_visualizar BOOLEAN DEFAULT true,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_table_id, user_id)
);

-- ============================================================================
-- VALIDADORES DE RELACIONAMENTO
-- ============================================================================

CREATE OR REPLACE FUNCTION validar_relacionamento_usuario()
RETURNS TRIGGER AS $$
DECLARE
  origem_owner UUID;
  destino_owner UUID;
BEGIN
  SELECT user_id INTO origem_owner FROM user_tables WHERE id = NEW.tabela_origem_id;
  SELECT user_id INTO destino_owner FROM user_tables WHERE id = NEW.tabela_destino_id;

  IF origem_owner IS NULL OR destino_owner IS NULL THEN
    RAISE EXCEPTION 'Tabela de origem ou destino não existe.';
  END IF;

  IF origem_owner <> auth.uid()::uuid OR destino_owner <> auth.uid()::uuid THEN
    RAISE EXCEPTION 'O relacionamento deve ser criado apenas entre tabelas do usuário autenticado.';
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_user_tables_user_id ON user_tables(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tables_nome_tabela ON user_tables(nome_tabela);
CREATE INDEX IF NOT EXISTS idx_user_table_columns_user_table_id ON user_table_columns(user_table_id);
CREATE INDEX IF NOT EXISTS idx_user_table_columns_nome_coluna ON user_table_columns(nome_coluna);
CREATE INDEX IF NOT EXISTS idx_user_table_relationships_user_id ON user_table_relationships(user_id);
CREATE INDEX IF NOT EXISTS idx_user_table_relationships_origem ON user_table_relationships(tabela_origem_id);
CREATE INDEX IF NOT EXISTS idx_user_table_data_user_table_id ON user_table_data(user_table_id);
CREATE INDEX IF NOT EXISTS idx_user_table_permissions_user_table_id ON user_table_permissions(user_table_id);
CREATE INDEX IF NOT EXISTS idx_user_table_permissions_user_id ON user_table_permissions(user_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE user_tables ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas suas tabelas" ON user_tables
  FOR SELECT USING (user_id = auth.uid()::uuid);
CREATE POLICY "Usuários inserem apenas tabelas para si mesmos" ON user_tables
  FOR INSERT WITH CHECK (user_id = auth.uid()::uuid);
CREATE POLICY "Usuários atualizam apenas suas próprias tabelas" ON user_tables
  FOR UPDATE USING (user_id = auth.uid()::uuid);
CREATE POLICY "Usuários deletam apenas suas próprias tabelas" ON user_tables
  FOR DELETE USING (user_id = auth.uid()::uuid);

ALTER TABLE user_table_columns ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas colunas de suas tabelas" ON user_table_columns
  FOR SELECT USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );
CREATE POLICY "Usuários inserem colunas apenas em suas tabelas" ON user_table_columns
  FOR INSERT WITH CHECK (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );
CREATE POLICY "Usuários atualizam apenas colunas de suas tabelas" ON user_table_columns
  FOR UPDATE USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );
CREATE POLICY "Usuários deletam apenas colunas de suas tabelas" ON user_table_columns
  FOR DELETE USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );

ALTER TABLE user_table_relationships ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas relacionamentos de suas tabelas" ON user_table_relationships
  FOR SELECT USING (
    user_id = auth.uid()::uuid
  );
CREATE POLICY "Usuários inserem relacionamentos apenas em suas tabelas" ON user_table_relationships
  FOR INSERT WITH CHECK (
    user_id = auth.uid()::uuid
  );
CREATE POLICY "Usuários atualizam apenas relacionamentos próprios" ON user_table_relationships
  FOR UPDATE USING (user_id = auth.uid()::uuid);
CREATE POLICY "Usuários deletam apenas relacionamentos próprios" ON user_table_relationships
  FOR DELETE USING (user_id = auth.uid()::uuid);

ALTER TABLE user_table_data ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas dados de suas tabelas" ON user_table_data
  FOR SELECT USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );
CREATE POLICY "Usuários inserem dados apenas em suas tabelas" ON user_table_data
  FOR INSERT WITH CHECK (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );
CREATE POLICY "Usuários atualizam apenas dados de suas tabelas" ON user_table_data
  FOR UPDATE USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );
CREATE POLICY "Usuários deletam apenas dados de suas tabelas" ON user_table_data
  FOR DELETE USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );

ALTER TABLE user_table_permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas permissões de suas tabelas ou que lhes foram concedidas" ON user_table_permissions
  FOR SELECT USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
    OR user_id = auth.uid()::uuid
  );
CREATE POLICY "Usuários inserem permissões apenas para suas tabelas" ON user_table_permissions
  FOR INSERT WITH CHECK (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );
CREATE POLICY "Usuários atualizam apenas permissões de suas tabelas" ON user_table_permissions
  FOR UPDATE USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );
CREATE POLICY "Usuários deletam apenas permissões de suas tabelas" ON user_table_permissions
  FOR DELETE USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = auth.uid()::uuid
    )
  );

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE OR REPLACE FUNCTION atualizar_timestamp_usuario_tabelas()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_tables BEFORE UPDATE ON user_tables
  FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp_usuario_tabelas();

CREATE TRIGGER trigger_update_user_table_columns BEFORE UPDATE ON user_table_columns
  FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp_usuario_tabelas();

CREATE TRIGGER trigger_update_user_table_relationships BEFORE UPDATE ON user_table_relationships
  FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp_usuario_tabelas();

CREATE TRIGGER trigger_update_user_table_data BEFORE UPDATE ON user_table_data
  FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp_usuario_tabelas();

CREATE TRIGGER trigger_update_user_table_permissions BEFORE UPDATE ON user_table_permissions
  FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp_usuario_tabelas();

-- ============================================================================
-- COMENTÁRIOS DE DOCUMENTAÇÃO
-- ============================================================================
COMMENT ON TABLE user_tables IS 'Metadados das tabelas criadas por cada usuário';
COMMENT ON TABLE user_table_columns IS 'Definição das colunas das tabelas do usuário';
COMMENT ON TABLE user_table_relationships IS 'Relacionamentos entre tabelas de cada usuário';
COMMENT ON TABLE user_table_data IS 'Dados de linha por tabela do usuário em formato JSONB';
COMMENT ON TABLE user_table_permissions IS 'Permissões de visualização/edição por usuário para cada tabela';
