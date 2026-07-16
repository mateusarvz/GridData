from fastapi import APIRouter, Depends
from typing import Annotated, List
from app.api.deps import TenantDBSession, CurrentUser
from app.modules.catalog.application.dto import (
    CreateWorkspaceDTO,
    WorkspaceResponseDTO,
    CreateFolderDTO,
    FolderResponseDTO,
    CreateTableDTO,
    TableResponseDTO,
    CreateColumnDTO,
    ColumnResponseDTO,
    CreateRelationshipDTO,
    RelationshipResponseDTO,
    WorkspaceTreeItemDTO,
    RenameItemDTO,
    MoveItemDTO
)
from app.modules.catalog.application.use_cases import (
    CreateWorkspaceUseCase,
    ListWorkspacesByOwnerUseCase,
    ListWorkspaceTreeUseCase,
    CreateFolderUseCase,
    RenameFolderUseCase,
    DeleteFolderUseCase,
    MoveFolderUseCase,
    CreateTableUseCase,
    RenameTableUseCase,
    DeleteTableUseCase,
    MoveTableUseCase,
    AddColumnUseCase,
    CreateRelationshipUseCase
)
from app.modules.catalog.infrastructure.repositories import (
    WorkspaceSQLAlchemyRepository,
    FolderSQLAlchemyRepository,
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

# ── Workspace ──

@router.post("/workspaces", response_model=WorkspaceResponseDTO)
async def create_workspace(dto: CreateWorkspaceDTO, session: TenantDBSession, _: SchemaAdmin):
    repo = WorkspaceSQLAlchemyRepository(session)
    use_case = CreateWorkspaceUseCase(repo)
    return await use_case.execute(dto)

@router.get("/workspaces", response_model=List[WorkspaceResponseDTO])
async def list_workspaces(session: TenantDBSession, current_user: CurrentUser):
    """Lista todos os workspaces do usuário autenticado."""
    repo = WorkspaceSQLAlchemyRepository(session)
    use_case = ListWorkspacesByOwnerUseCase(repo)
    owner_id = current_user.get("sub", "")
    return await use_case.execute(owner_id)

# ── Workspace Tree (flat list) ──

@router.get("/workspaces/{workspace_id}/tree", response_model=List[WorkspaceTreeItemDTO])
async def list_workspace_tree(workspace_id: str, session: TenantDBSession, _: CurrentUser):
    """Retorna todas as folders e tables de um workspace em lista flat."""
    f_repo = FolderSQLAlchemyRepository(session)
    t_repo = TableSQLAlchemyRepository(session)
    c_repo = ColumnSQLAlchemyRepository(session)
    use_case = ListWorkspaceTreeUseCase(f_repo, t_repo, c_repo)
    return await use_case.execute(workspace_id)

# ── Folders ──

@router.post("/workspaces/{workspace_id}/folders", response_model=FolderResponseDTO)
async def create_folder(workspace_id: str, dto: CreateFolderDTO, session: TenantDBSession, _: SchemaAdmin):
    # Override workspace_id from path
    dto_with_ws = CreateFolderDTO(name=dto.name, workspace_id=workspace_id, parent_id=dto.parent_id)
    repo = FolderSQLAlchemyRepository(session)
    use_case = CreateFolderUseCase(repo)
    return await use_case.execute(dto_with_ws)

@router.patch("/folders/{folder_id}", response_model=FolderResponseDTO)
async def rename_folder(folder_id: str, dto: RenameItemDTO, session: TenantDBSession, _: SchemaAdmin):
    repo = FolderSQLAlchemyRepository(session)
    use_case = RenameFolderUseCase(repo)
    return await use_case.execute(folder_id, dto)

@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(folder_id: str, session: TenantDBSession, _: SchemaAdmin):
    repo = FolderSQLAlchemyRepository(session)
    use_case = DeleteFolderUseCase(repo)
    await use_case.execute(folder_id)

@router.patch("/folders/{folder_id}/move", response_model=FolderResponseDTO)
async def move_folder(folder_id: str, dto: MoveItemDTO, session: TenantDBSession, _: SchemaAdmin):
    repo = FolderSQLAlchemyRepository(session)
    use_case = MoveFolderUseCase(repo)
    return await use_case.execute(folder_id, dto)

# ── Tables ──

@router.post("/tables", response_model=TableResponseDTO)
async def create_table(dto: CreateTableDTO, session: TenantDBSession, _: SchemaAdmin):
    t_repo = TableSQLAlchemyRepository(session)
    c_repo = ColumnSQLAlchemyRepository(session)
    use_case = CreateTableUseCase(t_repo, c_repo)
    return await use_case.execute(dto)

@router.patch("/tables/{table_id}", response_model=TableResponseDTO)
async def rename_table(table_id: str, dto: RenameItemDTO, session: TenantDBSession, _: SchemaAdmin):
    repo = TableSQLAlchemyRepository(session)
    use_case = RenameTableUseCase(repo)
    return await use_case.execute(table_id, dto)

@router.delete("/tables/{table_id}", status_code=204)
async def delete_table(table_id: str, session: TenantDBSession, _: SchemaAdmin):
    repo = TableSQLAlchemyRepository(session)
    use_case = DeleteTableUseCase(repo)
    await use_case.execute(table_id)

@router.patch("/tables/{table_id}/move", response_model=TableResponseDTO)
async def move_table(table_id: str, dto: MoveItemDTO, session: TenantDBSession, _: SchemaAdmin):
    repo = TableSQLAlchemyRepository(session)
    use_case = MoveTableUseCase(repo)
    return await use_case.execute(table_id, dto)

# ── Columns ──

@router.post("/tables/{table_id}/columns", response_model=ColumnResponseDTO)
async def add_column(table_id: str, dto: CreateColumnDTO, session: TenantDBSession, _: SchemaAdmin):
    t_repo = TableSQLAlchemyRepository(session)
    c_repo = ColumnSQLAlchemyRepository(session)
    use_case = AddColumnUseCase(t_repo, c_repo)
    return await use_case.execute(table_id, dto)

# ── Relationships ──

@router.post("/relationships", response_model=RelationshipResponseDTO)
async def create_relationship(dto: CreateRelationshipDTO, session: TenantDBSession, _: SchemaAdmin):
    t_repo = TableSQLAlchemyRepository(session)
    c_repo = ColumnSQLAlchemyRepository(session)
    r_repo = RelationshipSQLAlchemyRepository(session)
    use_case = CreateRelationshipUseCase(t_repo, c_repo, r_repo)
    return await use_case.execute(dto)
