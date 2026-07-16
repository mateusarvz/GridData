import asyncio
import sys
import logging
from dataclasses import dataclass
from typing import List, Optional
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MigrateAll")

@dataclass
class MigrationResult:
    tenant: str
    success: bool
    error: Optional[str] = None

async def migrate_single_tenant(tenant_name: str, semaphore: asyncio.Semaphore) -> MigrationResult:
    async with semaphore:
        logger.info(f"Iniciando migração para tenant: {tenant_name}")
        # Construir URL do banco do cliente
        # Em produção, pode vir de secret manager ou string de conexão do catálogo
        db_url = f"postgresql+asyncpg://postgres:postgres@localhost:5432/{tenant_name}"
        
        cmd = [
            sys.executable, "-m", "alembic", "-c", "alembic.ini",
            "-n", "tenants", "-x", f"db_url={db_url}", "upgrade", "head"
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"[SUCESSO] Tenant '{tenant_name}' atualizado com sucesso.")
                return MigrationResult(tenant=tenant_name, success=True)
            else:
                err_msg = stderr.decode().strip() or stdout.decode().strip()
                logger.error(f"[FALHA] Tenant '{tenant_name}' falhou: {err_msg}")
                return MigrationResult(tenant=tenant_name, success=False, error=err_msg)
        except Exception as e:
            logger.error(f"[ERRO EXCEPCIONAL] Tenant '{tenant_name}': {str(e)}")
            return MigrationResult(tenant=tenant_name, success=False, error=str(e))

async def migrate_all_tenants(tenant_names: List[str], max_concurrency: int = 5) -> List[MigrationResult]:
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [migrate_single_tenant(name, semaphore) for name in tenant_names]
    results = await asyncio.gather(*tasks)
    return list(results)

async def main():
    # Em execução real operacional, buscaria a lista de empresas ativas do DB do sistema:
    # select tenant_db_name from companies where is_deleted = false
    logger.info("Iniciando Script Runner Multi-Tenant Paralelo de Migrações...")
    
    # Exemplo fictício para rodar pela linha de comando ou via arg
    if len(sys.argv) > 1:
        tenants = sys.argv[1:]
    else:
        tenants = ["empresa_template", "empresa_acme", "empresa_dama"]
        
    results = await migrate_all_tenants(tenants, max_concurrency=5)
    
    success_count = sum(1 for r in results if r.success)
    failure_count = len(results) - success_count
    
    logger.info(f"=== Resumo Final de Migração: {success_count} sucesso(s), {failure_count} falha(s) ===")
    for r in results:
        if not r.success:
            logger.error(f" -> Falha em '{r.tenant}': {r.error}")
            
    if failure_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
