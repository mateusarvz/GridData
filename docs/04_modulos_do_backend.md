# Modulos Do Backend

## IAM

Responsável por autenticação, identidade e fluxo de acesso.

Arquivos relevantes:

- `backend/app/modules/iam/application/use_cases.py`
- `backend/app/modules/iam/presentation/routers/auth_router.py`
- `backend/app/modules/iam/presentation/routers/gemini_router.py`
- `backend/app/modules/iam/presentation/routers/supabase_login_router.py`

Funções principais:

- login
- geração de token
- validação de identidade
- integração com serviços externos

## Catalog

Guarda e expõe informações de catálogo do sistema.

Arquivos:

- `backend/app/modules/catalog/application/use_cases.py`
- `backend/app/modules/catalog/presentation/routers/catalog_router.py`
- `backend/app/modules/catalog/infrastructure/repositories.py`

Função:

- manter metadados organizados
- servir consultas de catálogo

## Engine

É a camada que lida com execução e composição de consultas.

Arquivos:

- `backend/app/modules/engine/application/use_cases.py`
- `backend/app/modules/engine/infrastructure/query_builder.py`
- `backend/app/modules/engine/presentation/routers/engine_router.py`

Função:

- montar consultas
- organizar persistência
- apoiar operações de schema e dados

## Audit

Mantém rastreabilidade de eventos importantes.

Arquivos:

- `backend/app/modules/audit/application/use_cases.py`
- `backend/app/modules/audit/presentation/routers/audit_router.py`
- `backend/app/modules/audit/infrastructure/repositories.py`

Função:

- registrar ações relevantes
- manter histórico do que mudou

## Data Session

Controla sessões temporárias de arquivos enviados.

Arquivos:

- `backend/app/modules/data_session/application/use_cases.py`
- `backend/app/modules/data_session/infrastructure/pandas_reader.py`
- `backend/app/modules/data_session/infrastructure/redis_data_session_store.py`
- `backend/app/modules/data_session/presentation/routers/data_session_router.py`

Função:

- guardar dados transitórios
- suportar upload e leitura de arquivos

## Schema Analysis

É o módulo mais importante para o produto.

Arquivos:

- `backend/app/modules/schema_analysis/application/use_cases.py`
- `backend/app/modules/schema_analysis/presentation/routers/schema_analysis_router.py`
- `backend/app/services/schema_stats_service.py`
- `backend/app/services/fk_candidate_service.py`
- `backend/app/services/gemini_schema_service.py`
- `backend/app/services/data_masking_service.py`

Função:

- analisar colunas
- sugerir tipos
- propor relacionamentos
- montar SQL final

