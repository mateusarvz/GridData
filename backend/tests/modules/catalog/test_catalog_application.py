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
from app.modules.catalog.application.dto import (
    CreateWorkspaceDTO,
    CreateTableDTO,
    CreateColumnDTO,
    CreateRelationshipDTO
)
from app.modules.catalog.application.use_cases import (
    CreateWorkspaceUseCase,
    CreateTableUseCase,
    AddColumnUseCase,
    CreateRelationshipUseCase
)
from app.modules.catalog.domain.value_objects import ColumnType, Cardinality
from app.shared.exceptions import DamaBoxDomainException

@pytest_asyncio.fixture
async def session_and_repos():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TenantBase.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        ws_repo = WorkspaceSQLAlchemyRepository(session)
        folder_repo = FolderSQLAlchemyRepository(session)
        table_repo = TableSQLAlchemyRepository(session)
        col_repo = ColumnSQLAlchemyRepository(session)
        rel_repo = RelationshipSQLAlchemyRepository(session)
        yield (session, ws_repo, folder_repo, table_repo, col_repo, rel_repo)
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_workspace_and_table_with_columns(session_and_repos):
    session, ws_repo, folder_repo, table_repo, col_repo, rel_repo = session_and_repos
    owner_id = str(uuid4())
    
    # 1. Create Workspace
    ws_uc = CreateWorkspaceUseCase(ws_repo)
    ws_res = await ws_uc.execute(CreateWorkspaceDTO(name="Comercial", owner_id=owner_id))
    assert ws_res.name == "Comercial"
    assert ws_res.owner_id == owner_id
    
    # 2. Create Table With Columns
    table_uc = CreateTableUseCase(table_repo, col_repo)
    table_dto = CreateTableDTO(
        name="Clientes",
        workspace_id=ws_res.id,
        columns=[
            CreateColumnDTO(name="Nome", slug="nome", col_type=ColumnType.TEXT.value, is_required=True),
            CreateColumnDTO(name="Email", slug="email", col_type=ColumnType.TEXT.value)
        ]
    )
    table_res = await table_uc.execute(table_dto)
    assert table_res.name == "Clientes"
    assert len(table_res.columns) == 2
    assert table_res.columns[0].name == "Nome"

@pytest.mark.asyncio
async def test_add_column_and_create_relationship(session_and_repos):
    session, ws_repo, folder_repo, table_repo, col_repo, rel_repo = session_and_repos
    owner_id = str(uuid4())
    
    ws_uc = CreateWorkspaceUseCase(ws_repo)
    ws = await ws_uc.execute(CreateWorkspaceDTO(name="Engenharia", owner_id=owner_id))
    
    table_uc = CreateTableUseCase(table_repo, col_repo)
    t1 = await table_uc.execute(CreateTableDTO(name="Projetos", workspace_id=ws.id, columns=[
        CreateColumnDTO(name="Título", slug="titulo", col_type=ColumnType.TEXT.value)
    ]))
    t2 = await table_uc.execute(CreateTableDTO(name="Tarefas", workspace_id=ws.id, columns=[
        CreateColumnDTO(name="Desc", slug="desc", col_type=ColumnType.TEXT.value)
    ]))
    
    # Add Column
    add_col_uc = AddColumnUseCase(table_repo, col_repo)
    new_col = await add_col_uc.execute(t2.id, CreateColumnDTO(
        name="Projeto Rel",
        slug="projeto_rel",
        col_type=ColumnType.RELATIONSHIP.value
    ))
    assert new_col.name == "Projeto Rel"
    
    # Create Relationship
    rel_uc = CreateRelationshipUseCase(table_repo, col_repo, rel_repo)
    rel_dto = CreateRelationshipDTO(
        name="Projeto -> Tarefas",
        source_table_id=t1.id,
        source_column_id=t1.columns[0].id,
        target_table_id=t2.id,
        target_column_id=new_col.id,
        cardinality=Cardinality.ONE_TO_MANY.value
    )
    rel_res = await rel_uc.execute(rel_dto)
    assert rel_res.cardinality == "one_to_many"
