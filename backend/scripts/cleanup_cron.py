import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_manager

# Modelos do Sistema
from app.modules.iam.infrastructure.orm_models import UserModel, CompanyModel

# Modelos dos Clientes (Tenants)
from app.modules.catalog.infrastructure.orm_models import (
    WorkspaceModel,
    FolderModel,
    TableModel,
    ColumnModel,
    RelationshipModel
)
from app.modules.engine.infrastructure.orm_models import DynamicRowModel
from app.modules.audit.infrastructure.orm_models import AuditLogModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CleanupCron")

async def purge_expired_soft_deletes(
    session: AsyncSession,
    model_classes: List[Any],
    retention_days: int = 30
) -> Dict[str, int]:
    """
    Purga (deleta fisicamente do banco de dados) registros que foram marcados com is_deleted=True
    há mais tempo que `retention_days`.
    """
    threshold_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    results = {}
    
    for model_cls in model_classes:
        table_name = getattr(model_cls, "__tablename__", str(model_cls))
        try:
            stmt = delete(model_cls).where(
                model_cls.is_deleted == True,
                model_cls.deleted_at < threshold_date
            )
            res = await session.execute(stmt)
            deleted_count = res.rowcount
            results[table_name] = deleted_count
            if deleted_count > 0:
                logger.info(f" -> [{table_name}]: {deleted_count} registro(s) purgado(s).")
        except Exception as e:
            logger.error(f"Erro ao purgar tabela {table_name}: {str(e)}")
            results[table_name] = -1
            
    await session.commit()
    return results

async def run_cleanup_system_db(retention_days: int = 30):
    logger.info("Iniciando purga no Banco de Dados do Sistema...")
    system_models = [UserModel, CompanyModel]
    async with db_manager.system_session_maker() as session:
        await purge_expired_soft_deletes(session, system_models, retention_days)

async def run_cleanup_tenant_db(tenant_db_name: str, retention_days: int = 30):
    logger.info(f"Iniciando purga no Banco do Tenant: {tenant_db_name}...")
    tenant_models = [
        WorkspaceModel,
        FolderModel,
        TableModel,
        ColumnModel,
        RelationshipModel,
        DynamicRowModel,
        AuditLogModel
    ]
    session_maker = db_manager.get_tenant_session_maker(tenant_db_name)
    async with session_maker() as session:
        await purge_expired_soft_deletes(session, tenant_models, retention_days)

async def main(retention_days: int = 30):
    logger.info(f"=== Worker Cron Noturno de Limpeza (Retenção: {retention_days} dias) ===")
    
    # 1. Limpar Banco Sistema
    await run_cleanup_system_db(retention_days)
    
    # 2. Listar Tenants Ativos e Limpar cada um em paralelo
    # Em produção: select tenant_db_name from companies where is_deleted = false
    tenants = ["empresa_template", "empresa_acme", "empresa_dama"]
    
    tasks = [run_cleanup_tenant_db(t, retention_days) for t in tenants]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("=== Purga Noturna Concluída com Sucesso ===")
    await db_manager.close_all_connections()

if __name__ == "__main__":
    asyncio.run(main())
