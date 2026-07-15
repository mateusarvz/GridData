import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.modules.catalog.infrastructure.orm_models import TenantBase
from app.modules.engine.domain.entities import DynamicRow
from app.modules.engine.infrastructure.repositories import DynamicRowSQLAlchemyRepository
from app.api.deps import get_tenant_session
from app.core.security import create_access_token

@pytest_asyncio.fixture
async def setup_audit_api():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    # Criar linha de teste no banco
    async with session_maker() as session:
        row = DynamicRow(
            table_id=uuid4(),
            data={"nome": "Empresa B", "status": "Ativo", "cotacao": 100},
            version=1,
            entity_id=UUID("00000000-0000-0000-0000-000000000002")
        )
        await DynamicRowSQLAlchemyRepository(session).save(row)
    
    async def override_get_tenant_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    yield engine
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_audit_api_endpoints_flow(setup_audit_api):
    user_id = str(uuid4())
    token = create_access_token({"sub": user_id, "role": "Member", "db": "test_db"})
    headers = {"Authorization": f"Bearer {token}"}
    row_id = "00000000-0000-0000-0000-000000000002"
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Inline Edit
        res_edit = await client.put(
            f"/api/v1/audit/rows/{row_id}/inline-edit",
            json={"new_data": {"nome": "Empresa B", "status": "Suspenso", "cotacao": 50}},
            headers=headers
        )
        assert res_edit.status_code == 200
        assert res_edit.json()["version"] == 2
        assert res_edit.json()["data"]["status"] == "Suspenso"
        
        # 2. Get History
        res_hist = await client.get(
            f"/api/v1/audit/rows/{row_id}/history",
            headers=headers
        )
        assert res_hist.status_code == 200
        history = res_hist.json()
        assert len(history) == 1
        assert history[0]["action"] == "update"
        assert history[0]["diff"]["status"]["old"] == "Ativo"
        
        # 3. Time Travel Revert (reverter para antes da mudança de versão 2)
        res_revert = await client.post(
            f"/api/v1/audit/rows/{row_id}/revert",
            json={"target_version": 2},
            headers=headers
        )
        assert res_revert.status_code == 200
        assert res_revert.json()["data"]["status"] == "Ativo"
        assert res_revert.json()["data"]["cotacao"] == 100
        assert res_revert.json()["version"] == 3
