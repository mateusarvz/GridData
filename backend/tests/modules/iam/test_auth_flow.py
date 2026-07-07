import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.modules.iam.infrastructure.orm_models import Base
from app.modules.iam.infrastructure.repositories import (
    UserSQLAlchemyRepository,
    CompanySQLAlchemyRepository,
    OrganizationMemberSQLAlchemyRepository
)
from app.modules.iam.domain.entities import User, Company, OrganizationMember
from app.modules.iam.domain.value_objects import RoleType
from app.core.security import get_password_hash
from app.api.deps import get_system_session

@pytest_asyncio.fixture
async def setup_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    # Criar dados
    async with session_maker() as session:
        u_repo = UserSQLAlchemyRepository(session)
        c_repo = CompanySQLAlchemyRepository(session)
        m_repo = OrganizationMemberSQLAlchemyRepository(session)
        
        user = User.create("api@dama.com", "API User", get_password_hash("Senha@123"))
        await u_repo.save(user)
        
        comp1 = Company.create("Empresa API 1", "empresa_api1")
        await c_repo.save(comp1)
        
        comp2 = Company.create("Empresa API 2", "empresa_api2")
        await c_repo.save(comp2)
        
        await m_repo.save(OrganizationMember.create(comp1.id, user.id, RoleType.OWNER))
        await m_repo.save(OrganizationMember.create(comp2.id, user.id, RoleType.MEMBER))

    async def override_get_system_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_system_session] = override_get_system_session
    
    yield (user, comp1, comp2)
    
    app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
async def test_auth_endpoints_login_refresh_and_switch(setup_test_db):
    user, comp1, comp2 = setup_test_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "api@dama.com", "password": "Senha@123"}
        )
        assert login_res.status_code == 200
        data = login_res.json()
        assert "access_token" in data
        assert data["company_id"] == str(comp1.id)
        assert data["database_name"] == "empresa_api1"
        
        # Verificar Cookie HttpOnly
        assert "refresh_token" in login_res.cookies
        refresh_cookie = login_res.cookies["refresh_token"]
        assert len(refresh_cookie) > 10

        # 2. Refresh Token via Cookie
        client.cookies.set("refresh_token", refresh_cookie)
        refresh_res = await client.post("/api/v1/auth/refresh")
        assert refresh_res.status_code == 200
        new_data = refresh_res.json()
        assert "access_token" in new_data
        assert len(new_data["access_token"]) > 20
        new_cookie = refresh_res.cookies["refresh_token"]
        assert new_cookie != refresh_cookie

        # 3. Switch Tenant
        switch_res = await client.post(
            "/api/v1/auth/switch-tenant",
            json={"target_company_id": str(comp2.id)},
            headers={"Authorization": f"Bearer {new_data['access_token']}"}
        )
        assert switch_res.status_code == 200
        switch_data = switch_res.json()
        assert switch_data["company_id"] == str(comp2.id)
        assert switch_data["database_name"] == "empresa_api2"
        assert switch_data["role"] == "Member"
