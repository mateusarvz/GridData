import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.modules.catalog.infrastructure.orm_models import TenantBase
from app.modules.catalog.infrastructure.repositories import (
    WorkspaceSQLAlchemyRepository,
    FolderSQLAlchemyRepository,
    TableSQLAlchemyRepository,
    ColumnSQLAlchemyRepository,
    RelationshipSQLAlchemyRepository
)
from app.modules.catalog.domain.entities import (
    Workspace,
    Folder,
    TableDefinition,
    ColumnDefinition,
    Relationship
)
from app.modules.catalog.domain.value_objects import ColumnType, Cardinality

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
async def test_workspace_folder_and_table_repositories(tenant_session: AsyncSession):
    ws_repo = WorkspaceSQLAlchemyRepository(tenant_session)
    folder_repo = FolderSQLAlchemyRepository(tenant_session)
    table_repo = TableSQLAlchemyRepository(tenant_session)
    
    ws = Workspace.create("Workspace Teste", owner_id=uuid4())
    await ws_repo.save(ws)
    
    folder = Folder.create("Folder Teste", workspace_id=ws.id)
    await folder_repo.save(folder)
    
    table = TableDefinition.create("Table Teste", workspace_id=ws.id, folder_id=folder.id)
    await table_repo.save(table)
    
    # Verificações
    fetched_ws = await ws_repo.get_by_id(ws.id)
    assert fetched_ws is not None
    assert fetched_ws.name == "Workspace Teste"
    
    folders = await folder_repo.list_by_workspace(ws.id)
    assert len(folders) == 1
    assert folders[0].name == "Folder Teste"
    
    tables = await table_repo.list_by_workspace(ws.id)
    assert len(tables) == 1
    assert tables[0].name == "Table Teste"

@pytest.mark.asyncio
async def test_column_and_relationship_repositories(tenant_session: AsyncSession):
    col_repo = ColumnSQLAlchemyRepository(tenant_session)
    rel_repo = RelationshipSQLAlchemyRepository(tenant_session)
    
    table_id = uuid4()
    col1 = ColumnDefinition.create(table_id, "Nome", "nome", ColumnType.TEXT, is_required=True, options={"max_len": 100})
    col2 = ColumnDefinition.create(table_id, "Idade", "idade", ColumnType.NUMBER)
    
    await col_repo.save(col1)
    await col_repo.save(col2)
    
    cols = await col_repo.list_by_table(table_id)
    assert len(cols) == 2
    assert cols[0].options.get("max_len") == 100
    
    rel = Relationship.create(
        "Pessoa Endereço",
        source_table_id=table_id,
        source_column_id=col1.id,
        target_table_id=uuid4(),
        target_column_id=uuid4(),
        cardinality=Cardinality.ONE_TO_MANY
    )
    await rel_repo.save(rel)
    
    rels = await rel_repo.list_by_table(table_id)
    assert len(rels) == 1
    assert rels[0].cardinality == Cardinality.ONE_TO_MANY
