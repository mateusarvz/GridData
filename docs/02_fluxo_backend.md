# Fluxo De Execução Do Backend

## Visão Geral

O backend trabalha em camadas.

Fluxo normal:

1. request entra na API
2. dependências validam contexto
3. router chama use case
4. use case consulta serviços e repositórios
5. resposta retorna em formato estável

## Fluxo De Login E Identidade

O módulo `iam` controla a autenticação.

Componentes principais:

- `backend/app/modules/iam/presentation/routers/auth_router.py`
- `backend/app/modules/iam/presentation/routers/supabase_login_router.py`
- `backend/app/modules/iam/application/use_cases.py`
- `backend/app/core/security.py`

Fluxo simplificado:

1. frontend envia credenciais
2. backend valida identidade
3. sistema gera token
4. token guarda informações úteis de contexto
5. frontend persiste sessão local

O token carrega dados como:

- `sub`
- `cid`
- `db`
- `role`

Esses campos ajudam na seleção do tenant correto.

## Fluxo De Sessão Do Tenant

`backend/app/api/deps.py` lê o token e injeta dados em `request.state`.

Depois disso:

- o `user_id` fica disponível
- o `tenant_db_name` fica disponível
- o `role` fica disponível

Esse design permite que várias rotas trabalhem com o contexto atual sem repetir lógica.

## Fluxo De Upload

O módulo `data_session` cuida da sessão temporária de arquivos.

Componentes:

- `backend/app/modules/data_session/presentation/routers/data_session_router.py`
- `backend/app/modules/data_session/application/use_cases.py`
- `backend/app/modules/data_session/infrastructure/pandas_reader.py`
- `backend/app/modules/data_session/infrastructure/redis_data_session_store.py`

Fluxo:

1. arquivo chega na API
2. backend identifica formato
3. pandas lê conteúdo
4. dados são convertidos em estrutura intermediária
5. sessão temporária armazena o estado

## Fluxo De Schema Analysis

Esse é o núcleo do produto.

Componentes:

- `backend/app/modules/schema_analysis/presentation/routers/schema_analysis_router.py`
- `backend/app/modules/schema_analysis/application/use_cases.py`
- `backend/app/services/schema_stats_service.py`
- `backend/app/services/fk_candidate_service.py`
- `backend/app/services/gemini_schema_service.py`
- `backend/app/services/data_masking_service.py`

### Etapas

1. criar sessão de análise
2. ler arquivos CSV, XLSX, XLS ou Parquet
3. calcular estatísticas de colunas
4. sugerir tipos de dados
5. detectar relacionamentos candidatos
6. consultar Gemini quando habilitado
7. salvar resultado em staging
8. permitir revisão manual
9. gerar SQL final no commit

## Exemplo De Tabelas De Staging

O fluxo usa tabelas intermediárias como:

- `schema_analysis_sessions`
- `schema_analysis_tables`
- `schema_analysis_relationships`
- `schema_analysis_rows`

Essas tabelas guardam:

- sessão atual
- arquivos carregados
- colunas inferidas
- relações sugeridas
- linhas para reconstrução do commit

## Fluxo De Commit

O commit final acontece em `CommitSessaoUseCase`.

Sequência:

1. valida sessão
2. busca tabelas e relações aprovadas
3. reconstrói linhas em memória
4. monta SQL determinístico
5. chama Gemini para refinamento, se disponível
6. executa SQL via RPC
7. limpa staging
8. marca sessão como confirmada

## Controle De Erros

Se algo falha:

- o use case devolve erro estruturado
- o frontend pode exibir mensagem amigável
- a auditoria registra eventos relevantes quando possível

## Segurança No Fluxo

As regras mais importantes são:

- cada use case valida `user_id`
- acesso a sessão precisa bater com o dono
- staging não deve vazar dados entre usuários
- tipos SQL aceitos são validados por whitelist
- identificadores de tabela e coluna são saneados

