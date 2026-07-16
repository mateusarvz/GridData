from fastapi import APIRouter, Depends
from typing import Annotated
from app.api.deps import TenantDBSession, CurrentUser
from app.modules.catalog.application.dto import (
    CreateWorkspaceDTO,
    WorkspaceResponseDTO,
    CreateTableDTO,
    TableResponseDTO,
    CreateColumnDTO,
    ColumnResponseDTO,
    CreateRelationshipDTO,
    RelationshipResponseDTO
)
from app.modules.catalog.application.use_cases import (
    CreateWorkspaceUseCase,
    CreateTableUseCase,
    AddColumnUseCase,
    CreateRelationshipUseCase
)
from app.modules.catalog.infrastructure.repositories import (
    WorkspaceSQLAlchemyRepository,
    TableSQLAlchemyRepository,
    ColumnSQLAlchemyRepository,
    RelationshipSQLAlchemyRepository
)
from app.shared.exceptions import DamaBoxDomainException

router = APIRouter(prefix="", tags=["Catalog & Schema Metadata"])

def require_schema_admin(current_user: CurrentUser):
    role = current_user.get("role")
    if role not in ("Owner", "Admin"):
        raise DamaBoxDomainException(
            detail="Apenas usuários com papel 'Owner' ou 'Admin' têm permissão para alterar metadados e schema.",
            title="Acesso Negado ao Schema",
            status_code=403
        )
    return current_user

SchemaAdmin = Annotated[dict, Depends(require_schema_admin)]

@router.post("/workspaces", response_model=WorkspaceResponseDTO)
async def create_workspace(dto: CreateWorkspaceDTO, session: TenantDBSession, _: SchemaAdmin):
    repo = WorkspaceSQLAlchemyRepository(session)
    use_case = CreateWorkspaceUseCase(repo)
    return await use_case.execute(dto)

@router.post("/tables", response_model=TableResponseDTO)
async def create_table(dto: CreateTableDTO, session: TenantDBSession, _: SchemaAdmin):
    t_repo = TableSQLAlchemyRepository(session)
    c_repo = ColumnSQLAlchemyRepository(session)
    use_case = CreateTableUseCase(t_repo, c_repo)
    return await use_case.execute(dto)

@router.post("/tables/{table_id}/columns", response_model=ColumnResponseDTO)
async def add_column(table_id: str, dto: CreateColumnDTO, session: TenantDBSession, _: SchemaAdmin):
    t_repo = TableSQLAlchemyRepository(session)
    c_repo = ColumnSQLAlchemyRepository(session)
    use_case = AddColumnUseCase(t_repo, c_repo)
    return await use_case.execute(table_id, dto)

@router.post("/relationships", response_model=RelationshipResponseDTO)
async def create_relationship(dto: CreateRelationshipDTO, session: TenantDBSession, _: SchemaAdmin):
    t_repo = TableSQLAlchemyRepository(session)
    c_repo = ColumnSQLAlchemyRepository(session)
    r_repo = RelationshipSQLAlchemyRepository(session)
    use_case = CreateRelationshipUseCase(t_repo, c_repo, r_repo)
    return await use_case.execute(dto)
