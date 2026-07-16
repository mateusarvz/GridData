# Arquitetura Do Backend

## Objetivo

O backend expõe a API principal da plataforma e concentra:

- autenticação
- regras de negócio
- integração com Supabase
- análise de schema
- persistência de staging
- auditoria

## Entrada Da Aplicação

O ponto de entrada é `backend/app/main.py`.

Ele:

- cria a instância FastAPI
- registra handlers de erro
- registra os routers dos módulos
- expõe endpoints de health check

## Configuração Central

`backend/app/core/config.py` centraliza valores de configuração.

Esse arquivo define:

- nome do projeto
- prefixo da API
- ambiente de execução
- URL do banco administrativo
- segredos de autenticação
- URLs e chaves de serviços externos

Esses valores devem vir de ambiente em produção.

## Camada De Banco

`backend/app/core/database.py` organiza o acesso a bancos PostgreSQL.

Existe uma distinção importante:

- banco administrativo, chamado `sistema`
- bancos de tenant, usados por empresas ou contextos separados

O gerenciador de banco:

- cria engine assíncrona
- cria session maker
- mantém cache de engines por tenant
- fecha conexões ao final

## Segurança

`backend/app/core/security.py` cuida de:

- criação de JWT
- leitura e validação de JWT
- expiração de token

`backend/app/api/deps.py` fornece dependências como:

- sessão do banco administrativo
- usuário atual
- sessão do tenant

## Integração Com Supabase

`backend/app/core/supabase.py` encapsula clientes Supabase.

Ele separa:

- client público para leitura básica
- client service role para operações administrativas

Esse ponto é importante porque o sistema usa Supabase como camada de persistência e integração.

## Tratamento De Erros

`backend/app/shared/error_handlers.py` e `backend/app/shared/exceptions.py` padronizam respostas.

O sistema usa uma abordagem consistente para:

- erros de domínio
- validação
- exceções HTTP

Isso facilita previsibilidade para frontend e testes.

## Módulos Principais

O backend é organizado por módulos:

- `iam`: autenticação e identidade
- `catalog`: catálogo de entidades e metadados
- `engine`: geração e execução de consultas
- `audit`: trilha de auditoria
- `data_session`: sessão de dados temporários
- `schema_analysis`: análise e inferência de esquema

Cada módulo segue uma divisão em:

- `domain`
- `application`
- `infrastructure`
- `presentation`

## Roteamento

`main.py` registra rotas como:

- `/api/v1/auth`
- `/api/v1/supabase`
- `/api/v1/catalog`
- `/api/v1/engine`
- `/api/v1/audit`
- `/api/v1/data-session`
- `/api/v1/schema-analysis`

Essa organização mantém o backend segmentado por responsabilidade.

## Scripts E Migrações

A pasta `backend/scripts/` contém scripts para:

- inicialização de banco
- migração de schema
- limpeza de tarefas agendadas
- migração em lote

O diretório `backend/alembic/` existe para migrações formais.

## Testes

`backend/tests/` cobre:

- segurança
- banco
- rotas
- integrações de módulos
- scripts de manutenção

Isso sugere foco em comportamento por domínio, não só em unidade isolada.

