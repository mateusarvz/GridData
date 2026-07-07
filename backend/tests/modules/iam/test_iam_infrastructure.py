import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.modules.iam.infrastructure.orm_models import Base
from app.modules.iam.infrastructure.repositories import (
    UserSQLAlchemyRepository,
    CompanySQLAlchemyRepository
)
from app.modules.iam.domain.entities import User, Company
from app.modules.iam.domain.value_objects import Email

@pytest_asyncio.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_user_repository_save_and_get(async_session: AsyncSession):
    repo = UserSQLAlchemyRepository(async_session)
    
    user = User.create(email="admin@dama.com", full_name="Admin Dama", password_hash="secret_hash")
    saved_user = await repo.save(user)
    
    # Buscar por ID
    fetched_by_id = await repo.get_by_id(user.id)
    assert fetched_by_id is not None
    assert fetched_by_id.id == user.id
    assert str(fetched_by_id.email) == "admin@dama.com"
    assert fetched_by_id.full_name == "Admin Dama"
    
    # Buscar por Email
    fetched_by_email = await repo.get_by_email(Email("admin@dama.com"))
    assert fetched_by_email is not None
    assert fetched_by_email.id == user.id

@pytest.mark.asyncio
async def test_company_repository_save_and_get(async_session: AsyncSession):
    repo = CompanySQLAlchemyRepository(async_session)
    
    company = Company.create(name="Empresa Dama", database_name="empresa_0001", cnpj="00000000000100")
    await repo.save(company)
    
    fetched = await repo.get_by_database_name("empresa_0001")
    assert fetched is not None
    assert fetched.name == "Empresa Dama"
    assert fetched.cnpj == "00000000000100"
