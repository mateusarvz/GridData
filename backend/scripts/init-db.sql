-- Habilitar extensão pgcrypto no banco administrativo 'sistema'
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Criar banco de cliente padrão para testes locais (empresa_0001)
CREATE DATABASE empresa_0001;

-- Conectar ao banco empresa_0001 e habilitar pgcrypto nele também
\c empresa_0001
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
