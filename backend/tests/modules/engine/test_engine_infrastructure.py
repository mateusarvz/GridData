import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.modules.catalog.infrastructure.orm_models import TenantBase
from app.modules.engine.infrastructure.orm_models import DynamicRowModel
from app.modules.engine.infrastructure.repositories import DynamicRowSQLAlchemyRepository
from app.modules.engine.domain.entities import DynamicRow
from app.modules.engine.domain.value_objects import FilterOperator

@pytest_asyncio.fixture
async def tenant_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_dynamic_row_repository_save_and_filter(tenant_session: AsyncSession):
    repo = DynamicRowSQLAlchemyRepository(tenant_session)
    table_id = uuid4()
    
    # Salvar linhas de teste
    r1 = DynamicRow.create(table_id, {"nome": "Davi", "status": "Ativo", "valor": 100})
    r2 = DynamicRow.create(table_id, {"nome": "Ana", "status": "Inativo", "valor": 200})
    r3 = DynamicRow.create(table_id, {"nome": "Lucas", "status": "Ativo", "valor": 300})
    
    await repo.save(r1)
    await repo.save(r2)
    await repo.save(r3)
    
    # 1. Listar sem filtros (paginação padrão)
    rows, total = await repo.list_by_table(table_id)
    assert total == 3
    assert len(rows) == 3
    
    # 2. Filtrar por EQ ("status" == "Ativo")
    filters_eq = [{"field": "status", "op": FilterOperator.EQ.value, "value": "Ativo"}]
    rows_eq, total_eq = await repo.list_by_table(table_id, filters=filters_eq)
    assert total_eq == 2
    assert all(r.data["status"] == "Ativo" for r in rows_eq)
    
    # 3. Ordenação por "valor" Decrescente
    rows_sort, _ = await repo.list_by_table(table_id, sort_by="valor", sort_desc=True)
    assert rows_sort[0].data["valor"] == 300
    assert rows_sort[1].data["valor"] == 200
    assert rows_sort[2].data["valor"] == 100
    
    # 4. Soft Delete / Hard Delete de linha
    await repo.delete(r1.id)
    _, total_after = await repo.list_by_table(table_id)
    assert total_after == 2
