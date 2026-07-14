-- ============================================================================
-- SCHEMA ESTRUTURAL DAMABOX
-- ============================================================================
-- Sistema de gerenciamento de tabelas multi-tenant com isolamento por usuário
-- Supabase Authentication + RLS (Row Level Security)
-- ============================================================================

-- ============================================================================
-- 1. USERS - Informações do usuário
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  nome_usuario VARCHAR(255) NOT NULL,
  avatar_url TEXT,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  ativo BOOLEAN DEFAULT true,
  CONSTRAINT email_valido CHECK (email ~ '^[^\s@]+@[^\s@]+\.[^\s@]+$')
);

-- ============================================================================
-- 2. SUBSCRIPTION PLANS - Planos de assinatura
-- ============================================================================
CREATE TABLE IF NOT EXISTS subscription_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nome VARCHAR(100) NOT NULL UNIQUE,
  descricao TEXT,
  preco_mensal DECIMAL(10, 2) NOT NULL,
  limite_tabelas INT DEFAULT 10,
  limite_linhas_por_tabela INT DEFAULT 100000,
  limite_armazenamento_mb INT DEFAULT 1000,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT preco_positivo CHECK (preco_mensal >= 0)
);

-- Inserir planos padrão
INSERT INTO subscription_plans (nome, descricao, preco_mensal, limite_tabelas, limite_linhas_por_tabela, limite_armazenamento_mb)
VALUES
  ('Free', 'Plano gratuito com limitações', 0.00, 2, 10000, 100),
  ('Pro', 'Plano profissional', 29.90, 50, 1000000, 10000),
  ('Enterprise', 'Plano empresarial', 99.90, 500, 10000000, 100000)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 3. USER SUBSCRIPTIONS - Assinatura do usuário
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan_id UUID NOT NULL REFERENCES subscription_plans(id),
  data_inicio DATE NOT NULL DEFAULT CURRENT_DATE,
  data_vencimento DATE NOT NULL,
  ativo BOOLEAN DEFAULT true,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id), -- Um usuário só pode ter uma assinatura ativa
  CONSTRAINT data_vencimento_futuro CHECK (data_vencimento > data_inicio)
);

-- ============================================================================
-- 4. USER TABLES - Tabelas criadas pelo usuário
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_tables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  nome_tabela VARCHAR(255) NOT NULL,
  descricao TEXT,
  nome_origem_arquivo VARCHAR(255), -- 'vendas.csv', 'contabilidade.parquet', etc
  tipo_arquivo VARCHAR(50), -- 'csv', 'parquet', 'excel', etc
  total_linhas INT DEFAULT 0,
  tamanho_mb DECIMAL(10, 2) DEFAULT 0,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP WITH TIME ZONE,
  UNIQUE(user_id, nome_tabela),
  CONSTRAINT nome_tabela_valido CHECK (nome_tabela ~ '^[a-zA-Z_][a-zA-Z0-9_]*$')
);

-- ============================================================================
-- 5. USER TABLE COLUMNS - Definição das colunas de cada tabela
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_table_columns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_table_id UUID NOT NULL REFERENCES user_tables(id) ON DELETE CASCADE,
  nome_coluna VARCHAR(255) NOT NULL,
  tipo_dado VARCHAR(50) NOT NULL, -- 'VARCHAR', 'INT', 'DECIMAL', 'TIMESTAMP', 'BOOLEAN', etc
  tamanho INT, -- Para VARCHAR(255), por exemplo
  permite_nulo BOOLEAN DEFAULT true,
  chave_primaria BOOLEAN DEFAULT false,
  chave_estrangeira BOOLEAN DEFAULT false,
  indice INT, -- Ordem da coluna
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_table_id, nome_coluna),
  CONSTRAINT nome_coluna_valido CHECK (nome_coluna ~ '^[a-zA-Z_][a-zA-Z0-9_]*$')
);

-- ============================================================================
-- 6. USER TABLE RELATIONSHIPS - Relacionamentos entre tabelas
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_table_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tabela_origem_id UUID NOT NULL REFERENCES user_tables(id) ON DELETE CASCADE,
  coluna_origem_id UUID NOT NULL REFERENCES user_table_columns(id) ON DELETE CASCADE,
  tabela_destino_id UUID NOT NULL REFERENCES user_tables(id) ON DELETE CASCADE,
  coluna_destino_id UUID NOT NULL REFERENCES user_table_columns(id) ON DELETE CASCADE,
  tipo_relacionamento VARCHAR(50) DEFAULT '1:N', -- '1:1', '1:N', 'N:N'
  nome_relacionamento VARCHAR(255),
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(tabela_origem_id, coluna_origem_id, tabela_destino_id, coluna_destino_id)
);

-- ============================================================================
-- 7. FILE UPLOADS - Histórico de uploads
-- ============================================================================
CREATE TABLE IF NOT EXISTS file_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  user_table_id UUID REFERENCES user_tables(id) ON DELETE SET NULL,
  nome_arquivo VARCHAR(255) NOT NULL,
  tipo_arquivo VARCHAR(50),
  caminho_arquivo TEXT,
  tamanho_bytes INT,
  total_linhas INT,
  status VARCHAR(50) DEFAULT 'processando', -- 'processando', 'sucesso', 'erro'
  mensagem_erro TEXT,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  processado_em TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 8. BILLING TRANSACTIONS - Transações de cobrança
-- ============================================================================
CREATE TABLE IF NOT EXISTS billing_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  subscription_id UUID REFERENCES user_subscriptions(id) ON DELETE SET NULL,
  tipo VARCHAR(50) NOT NULL, -- 'assinatura', 'ajuste', 'reembolso'
  valor DECIMAL(10, 2) NOT NULL,
  moeda VARCHAR(3) DEFAULT 'BRL',
  descricao TEXT,
  status VARCHAR(50) DEFAULT 'pendente', -- 'pendente', 'pago', 'falhou', 'cancelado'
  data_vencimento DATE,
  data_pagamento DATE,
  metodo_pagamento VARCHAR(50), -- 'cartao', 'pix', 'boleto'
  referencia_externa VARCHAR(255),
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 9. AUDIT LOGS - Auditoria de ações
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  acao VARCHAR(100) NOT NULL, -- 'criar_tabela', 'upload_arquivo', 'deletar_tabela', etc
  descricao TEXT,
  tabela_afetada VARCHAR(100),
  registro_id UUID,
  ip_address INET,
  user_agent TEXT,
  criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 10. INDEXES - Otimização de queries
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_plan_id ON user_subscriptions(plan_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_ativo ON user_subscriptions(ativo);
CREATE INDEX IF NOT EXISTS idx_user_tables_user_id ON user_tables(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tables_nome ON user_tables(nome_tabela);
CREATE INDEX IF NOT EXISTS idx_user_table_columns_user_table_id ON user_table_columns(user_table_id);
CREATE INDEX IF NOT EXISTS idx_user_table_relationships_user_id ON user_table_relationships(user_id);
CREATE INDEX IF NOT EXISTS idx_file_uploads_user_id ON file_uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_file_uploads_status ON file_uploads(status);
CREATE INDEX IF NOT EXISTS idx_billing_transactions_user_id ON billing_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_billing_transactions_status ON billing_transactions(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON audit_logs(user_id, acao, criado_em DESC);

-- ============================================================================
-- 11. ROW LEVEL SECURITY (RLS) - Isolamento por usuário
-- ============================================================================

-- USERS - Cada usuário vê apenas a si mesmo
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas a si mesmos" ON users
  FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Usuários atualizam apenas a si mesmos" ON users
  FOR UPDATE USING (auth.uid()::text = id::text);

-- USER_SUBSCRIPTIONS - Cada usuário vê apenas suas assinaturas
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas suas assinaturas" ON user_subscriptions
  FOR SELECT USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

-- USER_TABLES - Cada usuário acessa apenas suas tabelas
ALTER TABLE user_tables ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas suas tabelas" ON user_tables
  FOR SELECT USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

CREATE POLICY "Usuários inserem tabelas para si mesmos" ON user_tables
  FOR INSERT WITH CHECK (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

CREATE POLICY "Usuários atualizam apenas suas tabelas" ON user_tables
  FOR UPDATE USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

CREATE POLICY "Usuários deletam apenas suas tabelas" ON user_tables
  FOR DELETE USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

-- USER_TABLE_COLUMNS - Acesso via user_tables
ALTER TABLE user_table_columns ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários acessam colunas de suas tabelas" ON user_table_columns
  FOR SELECT USING (
    user_table_id IN (
      SELECT id FROM user_tables WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text)
    )
  );

-- FILE_UPLOADS - Cada usuário vê apenas seus uploads
ALTER TABLE file_uploads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas seus uploads" ON file_uploads
  FOR SELECT USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

-- BILLING_TRANSACTIONS - Cada usuário vê apenas suas transações
ALTER TABLE billing_transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas suas transações" ON billing_transactions
  FOR SELECT USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

-- AUDIT_LOGS - Cada usuário vê apenas seus logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Usuários veem apenas seus logs" ON audit_logs
  FOR SELECT USING (user_id = (SELECT id FROM users WHERE auth.uid()::text = users.id::text));

-- ============================================================================
-- 12. TRIGGERS - Automações
-- ============================================================================

-- Atualizar timestamp de atualização
CREATE OR REPLACE FUNCTION atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_users BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp();

CREATE TRIGGER trigger_update_user_subscriptions BEFORE UPDATE ON user_subscriptions
  FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp();

CREATE TRIGGER trigger_update_user_tables BEFORE UPDATE ON user_tables
  FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp();

CREATE TRIGGER trigger_update_billing_transactions BEFORE UPDATE ON billing_transactions
  FOR EACH ROW EXECUTE FUNCTION atualizar_timestamp();

-- ============================================================================
-- COMENTÁRIOS DE DOCUMENTAÇÃO
-- ============================================================================
COMMENT ON TABLE users IS 'Usuários do sistema - criados via Supabase Auth';
COMMENT ON TABLE subscription_plans IS 'Planos de assinatura disponíveis';
COMMENT ON TABLE user_subscriptions IS 'Assinatura ativa do usuário';
COMMENT ON TABLE user_tables IS 'Tabelas criadas pelos usuários via upload';
COMMENT ON TABLE user_table_columns IS 'Metadados das colunas das tabelas';
COMMENT ON TABLE user_table_relationships IS 'Relacionamentos entre tabelas do usuário';
COMMENT ON TABLE file_uploads IS 'Histórico de uploads de arquivos';
COMMENT ON TABLE billing_transactions IS 'Transações de cobrança e pagamentos';
COMMENT ON TABLE audit_logs IS 'Log de auditoria para segurança e compliance';
COMMENT ON TABLE subscription_plans IS 'Limite de tabelas e armazenamento por plano';

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.users TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.subscription_plans TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_subscriptions TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_tables TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_table_columns TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_table_relationships TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.file_uploads TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.billing_transactions TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.audit_logs TO service_role;
  END IF;
END
$$;