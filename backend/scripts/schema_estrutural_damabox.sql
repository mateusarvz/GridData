-- ============================================================================
-- SCHEMA ESTRUTURAL DAMABOX
-- public: user/account data only
-- table_schema: uploaded tables + schema analysis staging
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS table_schema;

-- ----------------------------------------------------------------------------
-- CLEANUP OF LEGACY TABLES IN public
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS public.user_table_relationships CASCADE;
DROP TABLE IF EXISTS public.user_table_columns CASCADE;
DROP TABLE IF EXISTS public.user_tables CASCADE;
DROP TABLE IF EXISTS public.schema_analysis_relationships CASCADE;
DROP TABLE IF EXISTS public.schema_analysis_tables CASCADE;

-- ----------------------------------------------------------------------------
-- PUBLIC TABLES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  nome_usuario VARCHAR(255) NOT NULL,
  avatar_url TEXT,
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  ativo BOOLEAN DEFAULT true,
  CONSTRAINT email_valido CHECK (email ~ '^[^\s@]+@[^\s@]+\.[^\s@]+$')
);

CREATE TABLE IF NOT EXISTS public.subscription_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nome VARCHAR(100) NOT NULL UNIQUE,
  descricao TEXT,
  preco_mensal DECIMAL(10, 2) NOT NULL,
  limite_tabelas INT DEFAULT 10,
  limite_linhas_por_tabela INT DEFAULT 100000,
  limite_armazenamento_mb INT DEFAULT 1000,
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT preco_positivo CHECK (preco_mensal >= 0)
);

INSERT INTO public.subscription_plans (
  nome, descricao, preco_mensal,
  limite_tabelas, limite_linhas_por_tabela, limite_armazenamento_mb
)
VALUES
  ('Free', 'Plano gratuito com limitacoes', 0.00, 2, 10000, 100),
  ('Pro', 'Plano profissional', 29.90, 50, 1000000, 10000),
  ('Enterprise', 'Plano empresarial', 99.90, 500, 10000000, 100000)
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS public.user_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  plan_id UUID NOT NULL REFERENCES public.subscription_plans(id),
  data_inicio DATE NOT NULL DEFAULT CURRENT_DATE,
  data_vencimento DATE NOT NULL,
  ativo BOOLEAN DEFAULT true,
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id),
  CONSTRAINT data_vencimento_futuro CHECK (data_vencimento > data_inicio)
);

CREATE TABLE IF NOT EXISTS public.file_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  users_table_id UUID,
  nome_arquivo VARCHAR(255) NOT NULL,
  tipo_arquivo VARCHAR(50),
  caminho_arquivo TEXT,
  tamanho_bytes INT,
  total_linhas INT,
  status VARCHAR(50) DEFAULT 'processando',
  mensagem_erro TEXT,
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  processado_em TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS public.billing_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  subscription_id UUID REFERENCES public.user_subscriptions(id) ON DELETE SET NULL,
  tipo VARCHAR(50) NOT NULL,
  valor DECIMAL(10, 2) NOT NULL,
  moeda VARCHAR(3) DEFAULT 'BRL',
  descricao TEXT,
  status VARCHAR(50) DEFAULT 'pendente',
  data_vencimento DATE,
  data_pagamento DATE,
  metodo_pagamento VARCHAR(50),
  referencia_externa VARCHAR(255),
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
  acao VARCHAR(100) NOT NULL,
  descricao TEXT,
  tabela_afetada VARCHAR(200),
  registro_id UUID,
  ip_address INET,
  user_agent TEXT,
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE_SCHEMA TABLES
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS table_schema.users_table (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  nome_tabela VARCHAR(255) NOT NULL,
  nome_origem_arquivo VARCHAR(255),
  tipo_arquivo VARCHAR(50),
  total_linhas INT DEFAULT 0,
  criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, nome_tabela),
  CONSTRAINT users_table_nome_valido CHECK (nome_tabela ~ '^[a-zA-Z_][a-zA-Z0-9_]*$')
);

CREATE INDEX IF NOT EXISTS idx_users_table_user_id ON table_schema.users_table(user_id);
CREATE INDEX IF NOT EXISTS idx_users_table_nome ON table_schema.users_table(nome_tabela);

-- ----------------------------------------------------------------------------
-- INDEXES (PUBLIC)
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON public.user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_plan_id ON public.user_subscriptions(plan_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_ativo ON public.user_subscriptions(ativo);
CREATE INDEX IF NOT EXISTS idx_file_uploads_user_id ON public.file_uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_file_uploads_status ON public.file_uploads(status);
CREATE INDEX IF NOT EXISTS idx_billing_transactions_user_id ON public.billing_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_billing_transactions_status ON public.billing_transactions(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON public.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON public.audit_logs(user_id, acao, criado_em DESC);

-- ----------------------------------------------------------------------------
-- RLS
-- ----------------------------------------------------------------------------
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.file_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE table_schema.users_table ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Usuarios veem apenas a si mesmos" ON public.users;
CREATE POLICY "Usuarios veem apenas a si mesmos" ON public.users
  FOR SELECT USING (auth.uid()::text = id::text);

DROP POLICY IF EXISTS "Usuarios atualizam apenas a si mesmos" ON public.users;
CREATE POLICY "Usuarios atualizam apenas a si mesmos" ON public.users
  FOR UPDATE USING (auth.uid()::text = id::text);

DROP POLICY IF EXISTS "Usuarios veem apenas suas assinaturas" ON public.user_subscriptions;
CREATE POLICY "Usuarios veem apenas suas assinaturas" ON public.user_subscriptions
  FOR SELECT USING (user_id = (SELECT id FROM public.users WHERE auth.uid()::text = users.id::text));

DROP POLICY IF EXISTS "Usuarios veem apenas seus uploads" ON public.file_uploads;
CREATE POLICY "Usuarios veem apenas seus uploads" ON public.file_uploads
  FOR SELECT USING (user_id = (SELECT id FROM public.users WHERE auth.uid()::text = users.id::text));

DROP POLICY IF EXISTS "Usuarios veem apenas suas transacoes" ON public.billing_transactions;
CREATE POLICY "Usuarios veem apenas suas transacoes" ON public.billing_transactions
  FOR SELECT USING (user_id = (SELECT id FROM public.users WHERE auth.uid()::text = users.id::text));

DROP POLICY IF EXISTS "Usuarios veem apenas seus logs" ON public.audit_logs;
CREATE POLICY "Usuarios veem apenas seus logs" ON public.audit_logs
  FOR SELECT USING (user_id = (SELECT id FROM public.users WHERE auth.uid()::text = users.id::text));

DROP POLICY IF EXISTS "Usuarios acessam apenas seus users_table" ON table_schema.users_table;
CREATE POLICY "Usuarios acessam apenas seus users_table" ON table_schema.users_table
  FOR ALL USING (user_id = (SELECT id FROM public.users WHERE auth.uid()::text = users.id::text));

-- ----------------------------------------------------------------------------
-- TRIGGERS
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_users ON public.users;
CREATE TRIGGER trigger_update_users BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION public.atualizar_timestamp();

DROP TRIGGER IF EXISTS trigger_update_user_subscriptions ON public.user_subscriptions;
CREATE TRIGGER trigger_update_user_subscriptions BEFORE UPDATE ON public.user_subscriptions
  FOR EACH ROW EXECUTE FUNCTION public.atualizar_timestamp();

DROP TRIGGER IF EXISTS trigger_update_billing_transactions ON public.billing_transactions;
CREATE TRIGGER trigger_update_billing_transactions BEFORE UPDATE ON public.billing_transactions
  FOR EACH ROW EXECUTE FUNCTION public.atualizar_timestamp();

-- ----------------------------------------------------------------------------
-- RPC TO EXECUTE SQL (service_role only)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.execute_sql(sql_query TEXT)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, table_schema
AS $$
BEGIN
  EXECUTE sql_query;
END;
$$;

REVOKE ALL ON FUNCTION public.execute_sql(TEXT) FROM PUBLIC;

-- ----------------------------------------------------------------------------
-- COMMENTS
-- ----------------------------------------------------------------------------
COMMENT ON TABLE public.users IS 'System users from Supabase Auth';
COMMENT ON TABLE public.subscription_plans IS 'Subscription plans';
COMMENT ON TABLE public.user_subscriptions IS 'Active user subscription';
COMMENT ON TABLE public.file_uploads IS 'Upload history';
COMMENT ON TABLE public.billing_transactions IS 'Billing and payments';
COMMENT ON TABLE public.audit_logs IS 'Security and compliance logs';
COMMENT ON TABLE table_schema.users_table IS 'Owner record for each uploaded logical table';

-- ----------------------------------------------------------------------------
-- GRANTS FOR service_role
-- ----------------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT USAGE ON SCHEMA public TO service_role;
    GRANT USAGE ON SCHEMA table_schema TO service_role;

    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.users TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.subscription_plans TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_subscriptions TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.file_uploads TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.billing_transactions TO service_role;
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.audit_logs TO service_role;

    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE table_schema.users_table TO service_role;

    GRANT EXECUTE ON FUNCTION public.execute_sql(TEXT) TO service_role;
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
