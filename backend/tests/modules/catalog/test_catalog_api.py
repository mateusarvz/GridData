import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.modules.catalog.infrastructure.orm_models import TenantBase
from app.api.deps import get_tenant_session, get_current_user
from app.core.security import create_access_token

@pytest_asyncio.fixture
async def setup_catalog_api():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async def override_get_tenant_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    yield engine
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_catalog_endpoints_with_admin_role(setup_catalog_api):
    owner_id = str(uuid4())
    token = create_access_token({"sub": owner_id, "role": "Owner", "db": "test_db"})
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create Workspace
        ws_res = await client.post(
            "/api/v1/catalog/workspaces",
            json={"name": "Comercial API", "owner_id": owner_id},
            headers=headers
        )
        assert ws_res.status_code == 200
        ws_data = ws_res.json()
        assert ws_data["name"] == "Comercial API"
        
        # 2. Create Table
        t_res = await client.post(
            "/api/v1/catalog/tables",
            json={
                "name": "Leads",
                "workspace_id": ws_data["id"],
                "columns": [{"name": "Empresa", "slug": "empresa", "col_type": "text"}]
            },
            headers=headers
        )
        assert t_res.status_code == 200
        t_data = t_res.json()
        assert t_data["name"] == "Leads"
        assert len(t_data["columns"]) == 1

@pytest.mark.asyncio
async def test_catalog_endpoints_forbidden_for_guest_role(setup_catalog_api):
    guest_id = str(uuid4())
    token = create_access_token({"sub": guest_id, "role": "Guest", "db": "test_db"})
    headers = {"Authorization": f"Bearer {token}"}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/catalog/workspaces",
            json={"name": "Não Permitido", "owner_id": guest_id},
            headers=headers
        )
        assert res.status_code == 403
        assert "permissão" in res.json()["detail"].lower()
