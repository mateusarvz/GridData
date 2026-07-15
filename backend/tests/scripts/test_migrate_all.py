import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from scripts.migrate_all import migrate_all_tenants, MigrationResult

@pytest.mark.asyncio
async def test_migrate_all_tenants_parallel_success_and_failure():
    tenants = ["empresa_a", "empresa_b", "empresa_c"]
    
    # Mock para simular migração: empresa_b falha, empresa_a e c passam
    async def mock_migrate_single(tenant_name: str, semaphore: asyncio.Semaphore) -> MigrationResult:
        async with semaphore:
            await asyncio.sleep(0.01) # Simula I/O assíncrono
            if tenant_name == "empresa_b":
                return MigrationResult(tenant=tenant_name, success=False, error="Connection refused")
            return MigrationResult(tenant=tenant_name, success=True, error=None)

    with patch("scripts.migrate_all.migrate_single_tenant", side_effect=mock_migrate_single):
        results = await migrate_all_tenants(tenants, max_concurrency=2)
        
        assert len(results) == 3
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        
        assert len(successes) == 2
        assert len(failures) == 1
        assert failures[0].tenant == "empresa_b"
        assert "Connection refused" in str(failures[0].error)
