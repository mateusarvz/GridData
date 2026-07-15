# Estratégia de Versionamento (Time Travel), Auditoria e Migrações Multi-Tenant — Dama Box

Este documento define as diretrizes operacionais de governança de dados, rastreabilidade imutável e evolução contínua de esquema no banco de dados **PostgreSQL** para o ecossistema **Dama Box**. Ele formaliza o mecanismo de **Time Travel** baseado em *JSON Diffing*, a segregação de logs por conformidade e a arquitetura de migrações assíncronas para múltiplos tenants usando **Alembic**.

---

## 1. Versionamento Diferencial de Dados (Time Travel via JSON Diff)

Para evitar a exaustão rápida de armazenamento no AWS RDS que ocorreria ao clonar planilhas inteiras a cada edição inline, a plataforma implementa um padrão de **CQRS Leve / Event Sourcing Diferencial**. A tabela de registros mantém o estado atualizado (`records.data_jsonb`), enquanto a tabela `record_version_history` armazena exclusivamente os deltas (*diffs*) mutacionais.

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário
    participant API as API FastAPI
    database DB as Banco do Cliente (empresa_xxxx)

    User->>API: PATCH /api/v1/records/rec_123/cells <br> { col_id: "col_price", new_value: 150.00 }
    API->>DB: SELECT data_jsonb FROM records WHERE id = 'rec_123'
    DB-->>API: Retorna Estado Anterior { "col_price": 100.00, "col_name": "Teclado" }
    
    API->>API: Calcula Delta (Diff): <br> { "col_price": { "old": 100.00, "new": 150.00 } }
    
    API->>DB: INICIA TRANSAÇÃO (BEGIN)
    API->>DB: UPDATE records SET data_jsonb = :novo_payload WHERE id = 'rec_123'
    API->>DB: INSERT INTO record_version_history (record_id, changed_by, diff_jsonb) <br> VALUES ('rec_123', 'usr_999', :diff_json)
    API->>DB: COMMIT
    API-->>User: 200 OK — Célula atualizada e versão histórica registrada
```

### 1.1. Estrutura do Payload de Versionamento (`diff_jsonb`)
O registro histórico armazena exclusivamente as chaves alteradas, preservando o tipo nativo original:
```json
{
  "spec_version": "1.0",
  "operation": "CELL_UPDATE",
  "changes": {
    "col_price": {
      "old_value": 100.00,
      "new_value": 150.00
    },
    "col_status": {
      "old_value": "Pendente",
      "new_value": "Aprovado"
    }
  }
}
```

### 1.2. Algoritmo de Reconstrução de Estado no Tempo ($T_x$) e Rollback
Para visualizar como uma planilha estava há 5 dias (Time Travel) ou reverter uma célula modificada por engano:
1. **Roll-Backward (Auditoria Visual):** O Backend busca o estado atual em `records.data_jsonb` e consulta os diffs em ordem cronológica decrescente (`ORDER BY changed_at DESC`) até o timestamp desejado $T_x$. A aplicação aplica as substituições reversas (`old_value`) em memória e devolve o snapshot ao Frontend.
2. **Rollback de Célula:** Quando o usuário clica em *"Reverter para esta versão"*, a API extrai o `old_value` do histórico alvo, executa um `PATCH` sobre o registro atual e gera um **novo evento de diff**, registrando que o dado foi restaurado a partir de uma versão anterior. A cadeia imutável de eventos nunca é apagada.

---

## 2. Segregação e Políticas de Auditoria (`Audit Logs`)

A plataforma separa as trilhas de auditoria em duas camadas com políticas de retenção distintas para atender a requisitos de compliance (LGPD/GDPR) sem onerar o banco operacional dos clientes.

| Camada de Auditoria | Tabela / Escopo | O que é Capturado | Prazo de Retenção | Destino Pós-Retenção |
| :--- | :--- | :--- | :---: | :--- |
| **Auditoria Global de Segurança** | `sistema.system_logs` | Logins, falhas de autenticação, força bruta, emissão de JWT, billing e criação/exclusão de Tenants. | **1 Ano (365 dias)** | Arquivado em formato Parquet no AWS S3 Glacier (Cold Storage). |
| **Auditoria Operacional do Tenant**| `empresa_xxxx.tenant_audit_logs` | Alterações de schema (colunas criadas/excluídas), ACL modificada, exclusões lógicas (Soft Delete) e exports de planilhas. | **30 Dias corridos** | Purgado fisicamente do banco de dados na rotina noturna. |

### 2.1. Rotina Automatizada de Limpeza Noturna (Purga)
Um *Cron Job* executado via **Celery** / **AWS EventBridge** roda todas as madrugadas às `03:00 AM UTC` em cada banco de cliente:
```sql
-- Exclui permanentemente logs operacionais expirados (> 30 dias)
DELETE FROM tenant_audit_logs 
WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';

-- Exclui permanentemente estruturas na Lixeira cujo prazo de 3 dias venceu
DELETE FROM workspaces WHERE is_deleted = TRUE AND deleted_at < CURRENT_TIMESTAMP - INTERVAL '3 days';
DELETE FROM table_definitions WHERE is_deleted = TRUE AND deleted_at < CURRENT_TIMESTAMP - INTERVAL '3 days';
```

---

## 3. Arquitetura de Migrações Multi-Tenant com Alembic

Em uma arquitetura de *Database-per-Tenant*, executar o comando tradicional `alembic upgrade head` atualizará apenas um único banco de dados. Para evoluir o esquema de milhares de empresas simultaneamente sem downtime ou travar conexões, o Dama Box adota uma **estratégia de duplo repositório de migrações** e um motor de deploy paralelo.

### 3.1. Estrutura de Pastas de Migração no Projeto
```text
backend/
├── alembic/
│   ├── system/                 # Migrações aplicáveis APENAS ao banco administrativo "sistema"
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial_system_schema.py
│   │
│   └── tenants/                # Migrações aplicáveis aos N bancos de clientes "empresa_xxxx"
│       ├── env.py
│       └── versions/
│           ├── 0001_initial_tenant_schema.py
│           └── 0002_add_gin_index_to_records.py
└── app/
    └── db/
        └── migrate_all.py      # Script de Execução Multi-Tenant Paralela
```

---

### 3.2. Script Customizado de Deploy Multi-Tenant (`migrate_all.py`)

O script abaixo é executado durante o processo de CI/CD (GitHub Actions / AWS CodePipeline) ou na inicialização dos containers ECS. Ele consulta a lista de empresas ativas no banco `sistema` e dispara o upgrade de esquema em paralelo usando um *Pool de Threads/AsyncIO* com tratamento isolado de falhas.

```python
import asyncio
import logging
from typing import List, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from alembic.config import Config
from alembic import command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DamaBox-MultiTenantMigrator")

SYSTEM_DB_URL = "postgresql+asyncpg://admin:secret@aws-rds-master:5432/sistema"

async def get_active_tenants() -> List[Dict[str, str]]:
    """Consulta o banco administrativo e retorna as coordenadas de conexão de todos os clientes ativos."""
    engine = create_async_engine(SYSTEM_DB_URL, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT database_name, database_host, database_port, database_user, database_password FROM companies WHERE is_active = TRUE")
        )
        tenants = [dict(row._mapping) for row in result]
    await engine.dispose()
    return tenants

def run_alembic_upgrade(db_url: str, tenant_name: str) -> bool:
    """Função síncrona que invoca o Alembic programaticamente para uma URL específica."""
    try:
        alembic_cfg = Config("alembic/tenants/alembic.ini")
        # Substitui dinamicamente a URL de conexão no arquivo de configuração em memória
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        logger.info(f"[{tenant_name}] Iniciando migração para 'head'...")
        command.upgrade(alembic_cfg, "head")
        logger.info(f"[{tenant_name}] ✔ Migração concluída com sucesso!")
        return True
    except Exception as e:
        logger.error(f"[{tenant_name}] ✖ FALHA CRÍTICA na migração: {str(e)}")
        return False

async def migrate_all_tenants():
    logger.info("================================================================")
    logger.info("INICIANDO DEPLOY DE MIGRAÇÕES MULTI-TENANT (ALEMBIC)")
    logger.info("================================================================")
    
    # 1. Primeiro, migrar o banco administrativo central "sistema"
    logger.info("[SISTEMA] Atualizando banco administrativo central...")
    sys_cfg = Config("alembic/system/alembic.ini")
    sys_cfg.set_main_option("sqlalchemy.url", SYSTEM_DB_URL.replace("+asyncpg", ""))
    command.upgrade(sys_cfg, "head")
    
    # 2. Consultar lista de bancos de clientes
    tenants = await get_active_tenants()
    logger.info(f"Total de Tenants ativos identificados para migração: {len(tenants)}")
    
    # 3. Executar migrações dos clientes no ThreadPoolExecutor para não travar o loop assíncrono
    loop = asyncio.get_running_loop()
    tasks = []
    
    for t in tenants:
        # Monta a URL síncrona (psycopg2/asyncpg compatível com Alembic CLI)
        url = f"postgresql://{t['database_user']}:{t['database_password']}@{t['database_host']}:{t['database_port']}/{t['database_name']}"
        tasks.append(loop.run_in_executor(None, run_alembic_upgrade, url, t['database_name']))
    
    # Executa em lotes paralelos
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 4. Relatório Final Consolidado
    sucessos = sum(1 for r in results if r is True)
    falhas = len(results) - sucessos
    
    logger.info("================================================================")
    logger.info(f"RELATÓRIO DE DEPLOY CONCLUÍDO: ✔ {sucessos} Sucessos | ✖ {falhas} Falhas")
    logger.info("================================================================")
    
    if falhas > 0:
        raise RuntimeError(f"O deploy de migração falhou em {falhas} bancos de clientes! Verifique os logs acima.")

if __name__ == "__main__":
    asyncio.run(migrate_all_tenants())
```

---

## 4. Governança e Testes de Migração

Para garantir que nenhuma migração quebre em produção sob carga de milhares de clientes:
1. **Regra Zero-Downtime:** Nenhuma migração em `alembic/tenants/` pode renomear ou deletar colunas em uso sem um período de transição em duas fases (*Expand and Contract Pattern*).
2. **Ambiente de Sandbox:** O script `migrate_all.py` deve rodar em um container de testes contra pelo menos 10 bancos de clientes simulados no CI antes do merge na branch `main`.
