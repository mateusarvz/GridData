import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.modules.catalog.infrastructure.orm_models import TenantBase
from app.modules.catalog.infrastructure.repositories import TableSQLAlchemyRepository
from app.modules.catalog.domain.entities import TableDefinition
from app.api.deps import get_tenant_session
from app.core.security import create_access_token

@pytest_asyncio.fixture
async def setup_engine_api():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    # Criar tabela inicial no banco para os testes
    async with session_maker() as session:
        table = TableDefinition(name="Contratos", workspace_id=uuid4(), entity_id=UUID("00000000-0000-0000-0000-000000000001"))
        await TableSQLAlchemyRepository(session).save(table)
    
    async def override_get_tenant_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    yield engine
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_engine_api_endpoints_flow(setup_engine_api):
    user_id = str(uuid4())
    token = create_access_token({"sub": user_id, "role": "Member", "db": "test_db"})
    headers = {"Authorization": f"Bearer {token}"}
    table_id = "00000000-0000-0000-0000-000000000001"
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create Row
        res_create = await client.post(
            f"/api/v1/engine/tables/{table_id}/rows",
            json={"data": {"cliente": "Empresa A", "status": "Ativo", "valor": 5000}},
            headers=headers
        )
        assert res_create.status_code == 200
        row_data = res_create.json()
        assert row_data["data"]["cliente"] == "Empresa A"
        row_id = row_data["id"]
        
        # 2. Query Rows with Filter
        res_query = await client.post(
            f"/api/v1/engine/tables/{table_id}/rows/query",
            json={"limit": 10, "offset": 0, "filters": [{"field": "status", "op": "eq", "value": "Ativo"}]},
            headers=headers
        )
        assert res_query.status_code == 200
        q_data = res_query.json()
        assert q_data["total"] == 1
        assert len(q_data["items"]) == 1
        
        # 3. Update Row
        res_update = await client.patch(
            f"/api/v1/engine/rows/{row_id}",
            json={"data": {"cliente": "Empresa A", "status": "Cancelado", "valor": 5000}},
            headers=headers
        )
        assert res_update.status_code == 200
        assert res_update.json()["data"]["status"] == "Cancelado"
        assert res_update.json()["version"] == 2
        
        # 4. Delete Row
        res_delete = await client.delete(
            f"/api/v1/engine/rows/{row_id}",
            headers=headers
        )
        assert res_delete.status_code == 200
        assert res_delete.json()["status"] == "deleted"
