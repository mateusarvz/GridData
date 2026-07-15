# Plano de Codificação e Implementação no Backend — Dama Box

> **Para Engenheiros e Subagentes de IA:** Este documento é o roteiro executivo (*Roadmap*) para a construção do Backend em **Python (FastAPI + SQLAlchemy 2.0)**. Todas as implementações devem seguir a metodologia **Test-Driven Development (TDD)** (escrever o teste falhando primeiro, implementar o código mínimo para passar e refatorar), mantendo commits atomizados por tarefa.

---

## 🎯 Visão Geral do Projeto
*   **Objetivo:** Construir um servidor de API RESTful multi-tenant de alto desempenho para gestão interativa de dados dinâmicos (planilhas avançadas, metadados em tempo de execução e Time Travel de 30 dias).
*   **Arquitetura:** Clean Architecture dividida em 4 camadas (`domain`, `application`, `infrastructure`, `presentation`) com isolamento físico de banco de dados no padrão *Database-per-Tenant* (PostgreSQL AWS RDS).
*   **Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (AsyncIO), Pydantic v2, Alembic, PyJWT, Argon2-cffi, Pytest, Testcontainers e Docker.

---

## 🌐 Diretrizes Globais de Engenharia
1. **Regra de Dependência (Clean Arch):** A camada `domain/` é puramente Python. Não deve conter imports do SQLAlchemy, FastAPI ou Pydantic. Todo o tráfego com o banco acontece via Interfaces ABC implementadas em `infrastructure/`.
2. **Invariante de Chave Primária:** Uso estrito de `UUIDv7` em todas as novas entidades criadas.
3. **Padrão de Respostas de Erro:** Exceções capturadas são mapeadas obrigatoriamente para o formato **RFC 7807 (Problem Details JSON)**.
4. **Soft Delete Universal:** Em entidades persistentes, exclusões chamam `soft_delete()` (`is_deleted = True, deleted_at = now()`), nunca `DELETE` físico direto no SQL operacional.

---

## 📅 Etapa 1: Fundação do Projeto e Infraestrutura Core (`backend/`)

### 📌 Tarefa 1.1: Scaffolding e Gerenciamento de Dependências
*   **Objetivo:** Inicializar o projeto Python com Poetry, Docker Compose e estrutura base.
*   **Arquivos a Criar:**
    *   `backend/pyproject.toml` (com dependências: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `pyjwt`, `argon2-cffi`, `pytest`, `pytest-asyncio`, `httpx`).
    *   `backend/docker-compose.yml` (PostgreSQL 16 com extensão `pgcrypto`, Redis 7 e MinIO S3).
    *   `backend/Dockerfile` e `backend/.env.example`.
*   **Comando de Verificação:** `docker compose up -d && poetry run pytest` (Deve passar com 0 testes falhando no scaffold).

### 📌 Tarefa 1.2: Módulo Core de Configuração e Segurança
*   **Objetivo:** Implementar carregamento de variáveis de ambiente tipadas e utilitários de criptografia.
*   **Arquivos a Criar:**
    *   `backend/app/core/config.py` (Classe `Settings(BaseSettings)` lendo `DATABASE_SYSTEM_URL`, `JWT_SECRET_KEY`, `ENVIRONMENT`).
    *   `backend/app/core/security.py` (Funções `verify_password()`, `get_password_hash()` usando Argon2id e `create_access_token()`).
*   **Testes Automatizados (`tests/core/test_security.py`):**
    *   `test_password_hashing_and_verification()`: Verifica se o hash gerado é diferente da senha clara e valida corretamente no verify.
    *   `test_jwt_generation_and_decoding()`: Garante que o token expira no tempo correto e preserva o payload.

### 📌 Tarefa 1.3: Gerenciador de Conexões Async e Pool Dinâmico de Tenants
*   **Objetivo:** Criar o mecanismo que gerencia o *pool* de conexões do banco administrativo (`sistema`) e o cache dinâmico de engines para os bancos dos clientes (`empresa_xxxx`).
*   **Arquivos a Criar:**
    *   `backend/app/core/database.py` (Classe singleton `TenantDatabaseManager` com dicionário `dict[str, AsyncEngine]` em cache).
    *   `backend/app/api/deps.py` (Dependências do FastAPI: `get_system_db` e `get_tenant_db`).
*   **Testes Automatizados (`tests/core/test_database_manager.py`):**
    *   `test_tenant_engine_caching()`: Conecta ao banco `sistema`, solicita conexão para `empresa_0001` e verifica se o segundo pedido retorna a engine em cache sem re-abrir socket.

### 📌 Tarefa 1.4: Interceptação Padrão RFC 7807
*   **Objetivo:** Criar tratadores de erro globais para formatar exceções no padrão IETF RFC 7807.
*   **Arquivos a Criar:**
    *   `backend/app/shared/exceptions.py` (Classe base `DamaBoxDomainException(Exception)`).
    *   `backend/app/shared/error_handlers.py` (Handlers para `RequestValidationError`, `HTTPException` e `DamaBoxDomainException`).
    *   `backend/app/main.py` (Registro das rotas e handlers).

---

## 📅 Etapa 2: Módulo IAM e Autenticação (Banco `sistema`)

### 📌 Tarefa 2.1: Domínio e Repositórios ABC (`iam/domain/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/iam/domain/entities.py` (`User`, `Organization`, `OrganizationMember`, `Invitation`).
    *   `backend/app/modules/iam/domain/value_objects.py` (`Email`, `PasswordHash`, `RoleType`).
    *   `backend/app/modules/iam/domain/repositories.py` (`IUserRepository(ABC)`, `IOrganizationRepository(ABC)`).

### 📌 Tarefa 2.2: Infraestrutura ORM (`iam/infrastructure/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/iam/infrastructure/orm_models.py` (Mapeamento SQLAlchemy 2.0 para tabelas `users`, `companies`, `organization_members`, `refresh_tokens`).
    *   `backend/app/modules/iam/infrastructure/repositories.py` (Implementação do `UserSQLAlchemyRepository` no Postgres).

### 📌 Tarefa 2.3: Casos de Uso e Lógica de Aplicação (`iam/application/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/iam/application/dto.py` (`LoginRequestDTO`, `TokenResponseDTO`, `SwitchTenantDTO`).
    *   `backend/app/modules/iam/application/use_cases.py`:
        *   `AuthenticateUserUseCase`: Valida senha, gera JWT (10 min) e Refresh Token opaco salvando hash no banco.
        *   `RefreshTokenUseCase`: Invalida o token antigo, aplica rotação e retorna novo par.
        *   `SwitchTenantUseCase`: Verifica se o usuário pertence à empresa alvo e emite novo JWT escopado.

### 📌 Tarefa 2.4: Routers e Segurança de Cookie (`iam/presentation/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/iam/presentation/routers/auth_router.py` (Rotas `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/switch-tenant`).
    *   `backend/app/api/deps.py` (Atualização: adicionar dependência `get_current_user` decodificando o JWT Header).
*   **Testes de Integração (`tests/modules/iam/test_auth_flow.py`):**
    *   `test_login_success_returns_jwt_and_httponly_cookie()`
    *   `test_refresh_token_rotation_and_reuse_detection()`
    *   `test_switch_tenant_forbids_unauthorized_company()`

---

## 📅 Etapa 3: Módulo Catalog — Metadados no Banco de Clientes (`empresa_xxxx`)

### 📌 Tarefa 3.1: Domínio de Catálogo (`catalog/domain/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/catalog/domain/entities.py` (`Workspace`, `Folder`, `TableDefinition`, `ColumnDefinition`, `Relationship`).
    *   `backend/app/modules/catalog/domain/value_objects.py` (`ColumnType`, `Cardinality`).
    *   `backend/app/modules/catalog/domain/repositories.py` (`IWorkspaceRepository(ABC)`, `ITableRepository(ABC)`).

### 📌 Tarefa 3.2: Infraestrutura ORM no Banco do Tenant (`catalog/infrastructure/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/catalog/infrastructure/orm_models.py` (Tabelas `workspaces`, `folders`, `table_definitions`, `column_definitions`, `relationships`).
    *   `backend/app/modules/catalog/infrastructure/repositories.py` (`TableSQLAlchemyRepository`).

### 📌 Tarefa 3.3: Casos de Uso e Unit of Work (`catalog/application/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/catalog/application/use_cases.py`:
        *   `CreateTableDefinitionUseCase`: Cria tabela no workspace alvo com colunas padrão iniciadas via `UoW`.
        *   `AddColumnUseCase`: Adiciona coluna validando regras de negócio e limites de schema (máx 200 colunas).

### 📌 Tarefa 3.4: Routers e Autorização Granular (`catalog/presentation/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/catalog/presentation/routers/tables_router.py` (`POST /api/v1/workspaces/{id}/tables`, `POST /api/v1/tables/{id}/columns`).
    *   `backend/app/api/deps.py` (Adição: dependência `RequirePermission(action="table:alter_schema")` avaliando ACL no banco do cliente).
*   **Testes de Integração (`tests/modules/catalog/test_catalog_crud.py`):**
    *   `test_create_table_definition_in_workspace()`
    *   `test_acl_permission_override_for_guest_user()`

---

## 📅 Etapa 4: Módulo Engine — Dados Dinâmicos em JSONB e Índice GIN

### 📌 Tarefa 4.1: Domínio do Engine e Células (`engine/domain/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/engine/domain/entities.py` (`Record`, `FileAttachment`).
    *   `backend/app/modules/engine/domain/value_objects.py` (`DynamicPayload` encapsulando validação de tipagem perante as colunas).
    *   `backend/app/modules/engine/domain/repositories.py` (`IRecordRepository(ABC)`).

### 📌 Tarefa 4.2: Query Builder para Otimização GIN (`engine/infrastructure/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/engine/infrastructure/orm_models.py` (Tabela `records` com coluna `data_jsonb JSONB NOT NULL DEFAULT '{}'`).
    *   `backend/app/modules/engine/infrastructure/jsonb_query_builder.py` (Módulo utilitário para construir queries dinâmicas usando o operador `@>` e `jsonb_path_ops` no Postgres para paginação e ordenação por coluna JSONB).
    *   `backend/app/modules/engine/infrastructure/repositories.py` (`RecordSQLAlchemyRepository`).

### 📌 Tarefa 4.3: Casos de Uso Interativos (`engine/application/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/engine/application/use_cases.py`:
        *   `InsertRecordUseCase`: Valida os tipos de cada chave no payload em relação ao catalog antes do insert na planilha.
        *   `QueryDynamicRecordsUseCase`: Executa consulta paginada aplicando filtros dinâmicos no JSONB.

### 📌 Tarefa 4.4: Routers de Planilha (`engine/presentation/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/engine/presentation/routers/records_router.py` (`GET /api/v1/tables/{tid}/records`, `POST /api/v1/tables/{tid}/records`).
*   **Testes de Alta Performance (`tests/modules/engine/test_jsonb_gin_queries.py`):**
    *   `test_insert_record_validates_column_types()`
    *   `test_gin_index_filtering_on_dynamic_jsonb_cells()`

---

## 📅 Etapa 5: Módulo Audit & Time Travel (Versionamento Diferencial)

### 📌 Tarefa 5.1: Domínio e Algoritmo de Diferença (`audit/domain/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/audit/domain/entities.py` (`RecordVersion`, `TenantAuditLog`).
    *   `backend/app/modules/audit/domain/diff_engine.py` (Função pura `compute_jsonb_diff(old_dict, new_dict) -> dict` calculando deltas enxutos).

### 5.2: Caso de Uso de Edição Inline e Reversão (`audit/application/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/audit/application/use_cases.py`:
        *   `UpdateCellUseCase`: Aplica `PATCH` na célula em `records`, calcula o delta com `diff_engine` e grava de forma atômica na tabela `record_version_history`.
        *   `RollbackCellUseCase`: Reverte a célula para o valor em um timestamp passado e emite novo evento histórico.

### 📌 Tarefa 5.3: Routers de Histórico (`audit/presentation/`)
*   **Arquivos a Criar:**
    *   `backend/app/modules/audit/presentation/routers/history_router.py` (`PATCH /api/v1/records/{rid}/cells`, `GET /api/v1/records/{rid}/history`, `POST /api/v1/records/{rid}/rollback`).
*   **Testes de Integração (`tests/modules/audit/test_time_travel.py`):**
    *   `test_patch_cell_creates_immutable_diff_version()`
    *   `test_rollback_cell_restores_previous_value_and_logs_event()`

---

## 📅 Etapa 6: Automação Operacional e Migrações Alembic Multi-Tenant

### 📌 Tarefa 6.1: Configuração Dual do Alembic
*   **Arquivos a Criar:**
    *   `backend/alembic/system/env.py` e `backend/alembic/system/alembic.ini` (Apontando para os ORM models de IAM no banco `sistema`).
    *   `backend/alembic/tenants/env.py` e `backend/alembic/tenants/alembic.ini` (Apontando para os ORM models de Catalog, Engine e Audit).

### 📌 Tarefa 6.2: Script Runner Multi-Tenant Paralelo
*   **Arquivos a Criar:**
    *   `backend/app/db/migrate_all.py` (Script AsyncIO que lê `sistema.companies`, conecta em paralelo aos N bancos de clientes e executa `command.upgrade(config, "head")` com agregação de erros).

### 📌 Tarefa 6.3: Worker Cron para Purga Noturna (Celery / Asyncio)
*   **Arquivos a Criar:**
    *   `backend/app/workers/cleanup_cron.py` (Rotina noturna que apaga `tenant_audit_logs` > 30 dias e remove da Lixeira registros expirados).
*   **Testes Operacionais (`tests/db/test_multi_tenant_migrations.py`):**
    *   `test_migrate_all_script_upgrades_multiple_tenant_databases_concurrently()`

---

## ✅ Checklist de Pronto (Definition of Done — DoD)

Antes de considerar qualquer etapa de codificação como concluída e pronta para merge na branch `main`, verifique:
* [ ] Todo o código de negócio está dentro da camada `domain/` sem acoplamento a frameworks externos.
* [ ] Os testes de unidade e integração com `pytest` e banco em container Docker passam em 100% das asserções.
* [ ] Nenhuma consulta em endpoints protegidos deixa de injetar e respeitar o Tenant (`company_id`).
* [ ] Toda exceção lançada na API retorna JSON canônico RFC 7807 (`type`, `title`, `status`, `detail`).
* [ ] Os endpoints OpenAPI foram verificados na documentação interativa Swagger (`/docs`).
