import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.modules.catalog.infrastructure.orm_models import TenantBase
from app.modules.catalog.infrastructure.repositories import TableSQLAlchemyRepository
from app.modules.catalog.domain.entities import TableDefinition
from app.modules.engine.infrastructure.repositories import DynamicRowSQLAlchemyRepository
from app.modules.engine.application.dto import (
    CreateRowDTO,
    UpdateRowDTO,
    ListRowsQueryDTO
)
from app.modules.engine.application.use_cases import (
    CreateRowUseCase,
    UpdateRowUseCase,
    ListRowsUseCase,
    DeleteRowUseCase
)
from app.shared.exceptions import DamaBoxDomainException

@pytest_asyncio.fixture
async def session_and_repos():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        table_repo = TableSQLAlchemyRepository(session)
        row_repo = DynamicRowSQLAlchemyRepository(session)
        
        # Criar tabela de teste
        table = TableDefinition.create("Leads", workspace_id=uuid4())
        await table_repo.save(table)
        
        yield (session, table_repo, row_repo, table)
    await engine.dispose()

@pytest.mark.asyncio
async def test_engine_crud_use_cases(session_and_repos):
    _, table_repo, row_repo, table = session_and_repos
    table_id = str(table.id)
    
    # 1. Create Row
    create_uc = CreateRowUseCase(table_repo, row_repo)
    row_dto = CreateRowDTO(data={"nome": "Empresa X", "status": "Novo", "valor": 500})
    res_row = await create_uc.execute(table_id, row_dto)
    assert res_row.table_id == table_id
    assert res_row.data["nome"] == "Empresa X"
    assert res_row.version == 1
    
    # 2. Update Row
    update_uc = UpdateRowUseCase(row_repo)
    up_dto = UpdateRowDTO(data={"nome": "Empresa X", "status": "Em Negociação", "valor": 1000})
    up_res = await update_uc.execute(res_row.id, up_dto)
    assert up_res.data["status"] == "Em Negociação"
    assert up_res.version == 2
    
    # 3. List Rows with Filter
    list_uc = ListRowsUseCase(row_repo)
    query_dto = ListRowsQueryDTO(
        limit=10,
        offset=0,
        filters=[{"field": "status", "op": "eq", "value": "Em Negociação"}]
    )
    list_res = await list_uc.execute(table_id, query_dto)
    assert list_res.total == 1
    assert len(list_res.items) == 1
    
    # 4. Delete Row
    del_uc = DeleteRowUseCase(row_repo)
    del_res = await del_uc.execute(res_row.id)
    assert del_res is True
    
    list_empty = await list_uc.execute(table_id, ListRowsQueryDTO())
    assert list_empty.total == 0
