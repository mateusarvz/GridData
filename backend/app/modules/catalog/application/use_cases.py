from uuid import UUID
from typing import List
from datetime import datetime, timezone
from app.modules.catalog.domain.repositories import (
    IWorkspaceRepository,
    IFolderRepository,
    ITableRepository,
    IColumnRepository,
    IRelationshipRepository
)
from app.modules.catalog.domain.entities import (
    Workspace,
    Folder,
    TableDefinition,
    ColumnDefinition,
    Relationship
)
from app.modules.catalog.domain.value_objects import ColumnType, Cardinality
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
from app.shared.exceptions import DamaBoxDomainException

class CreateWorkspaceUseCase:
    def __init__(self, workspace_repo: IWorkspaceRepository):
        self.workspace_repo = workspace_repo

    async def execute(self, dto: CreateWorkspaceDTO) -> WorkspaceResponseDTO:
        ws = Workspace.create(name=dto.name, owner_id=UUID(dto.owner_id))
        saved = await self.workspace_repo.save(ws)
        return WorkspaceResponseDTO(
            id=str(saved.id),
            name=saved.name,
            owner_id=str(saved.owner_id)
        )

class ListWorkspacesByOwnerUseCase:
    def __init__(self, workspace_repo: IWorkspaceRepository):
        self.workspace_repo = workspace_repo

    async def execute(self, owner_id: str) -> List[WorkspaceResponseDTO]:
        workspaces = await self.workspace_repo.list_by_owner(UUID(owner_id))
        return [
            WorkspaceResponseDTO(
                id=str(ws.id),
                name=ws.name,
                owner_id=str(ws.owner_id)
            )
            for ws in workspaces
        ]

class ListWorkspaceTreeUseCase:
    def __init__(
        self,
        folder_repo: IFolderRepository,
        table_repo: ITableRepository,
        col_repo: IColumnRepository
    ):
        self.folder_repo = folder_repo
        self.table_repo = table_repo
        self.col_repo = col_repo

    async def execute(self, workspace_id: str) -> List[WorkspaceTreeItemDTO]:
        ws_uuid = UUID(workspace_id)
        folders = await self.folder_repo.list_by_workspace(ws_uuid)
        tables = await self.table_repo.list_by_workspace(ws_uuid)

        items: List[WorkspaceTreeItemDTO] = []

        for f in folders:
            items.append(WorkspaceTreeItemDTO(
                id=str(f.id),
                type="folder",
                name=f.name,
                parent_id=str(f.parent_id) if f.parent_id else None,
                column_count=None,
                created_at=f.created_at.isoformat(),
                updated_at=f.updated_at.isoformat()
            ))

        for t in tables:
            cols = await self.col_repo.list_by_table(t.id)
            items.append(WorkspaceTreeItemDTO(
                id=str(t.id),
                type="table",
                name=t.name,
                parent_id=str(t.folder_id) if t.folder_id else None,
                column_count=len(cols),
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat()
            ))

        return items

class CreateFolderUseCase:
    def __init__(self, folder_repo: IFolderRepository):
        self.folder_repo = folder_repo

    async def execute(self, dto: CreateFolderDTO) -> FolderResponseDTO:
        parent_id = UUID(dto.parent_id) if dto.parent_id else None
        folder = Folder.create(
            name=dto.name,
            workspace_id=UUID(dto.workspace_id),
            parent_id=parent_id
        )
        saved = await self.folder_repo.save(folder)
        return FolderResponseDTO(
            id=str(saved.id),
            name=saved.name,
            workspace_id=str(saved.workspace_id),
            parent_id=str(saved.parent_id) if saved.parent_id else None
        )

class RenameFolderUseCase:
    def __init__(self, folder_repo: IFolderRepository):
        self.folder_repo = folder_repo

    async def execute(self, folder_id: str, dto: RenameItemDTO) -> FolderResponseDTO:
        folder = await self.folder_repo.get_by_id(UUID(folder_id))
        if not folder:
            raise DamaBoxDomainException("Pasta não encontrada.", status_code=404)
        folder.name = dto.name
        folder.updated_at = datetime.now(timezone.utc)
        saved = await self.folder_repo.save(folder)
        return FolderResponseDTO(
            id=str(saved.id),
            name=saved.name,
            workspace_id=str(saved.workspace_id),
            parent_id=str(saved.parent_id) if saved.parent_id else None
        )

class DeleteFolderUseCase:
    def __init__(self, folder_repo: IFolderRepository):
        self.folder_repo = folder_repo

    async def execute(self, folder_id: str) -> None:
        folder = await self.folder_repo.get_by_id(UUID(folder_id))
        if not folder:
            raise DamaBoxDomainException("Pasta não encontrada.", status_code=404)
        folder.soft_delete()
        await self.folder_repo.save(folder)

class MoveFolderUseCase:
    def __init__(self, folder_repo: IFolderRepository):
        self.folder_repo = folder_repo

    async def execute(self, folder_id: str, dto: MoveItemDTO) -> FolderResponseDTO:
        folder = await self.folder_repo.get_by_id(UUID(folder_id))
        if not folder:
            raise DamaBoxDomainException("Pasta não encontrada.", status_code=404)

        new_parent = UUID(dto.new_parent_id) if dto.new_parent_id else None

        # Prevent moving a folder into itself
        if new_parent and str(new_parent) == folder_id:
            raise DamaBoxDomainException("Não é possível mover uma pasta para dentro de si mesma.", status_code=400)

        folder.parent_id = new_parent
        folder.updated_at = datetime.now(timezone.utc)
        saved = await self.folder_repo.save(folder)
        return FolderResponseDTO(
            id=str(saved.id),
            name=saved.name,
            workspace_id=str(saved.workspace_id),
            parent_id=str(saved.parent_id) if saved.parent_id else None
        )

class CreateTableUseCase:
    def __init__(self, table_repo: ITableRepository, col_repo: IColumnRepository):
        self.table_repo = table_repo
        self.col_repo = col_repo

    async def execute(self, dto: CreateTableDTO) -> TableResponseDTO:
        folder_id = UUID(dto.folder_id) if dto.folder_id else None
        table = TableDefinition.create(name=dto.name, workspace_id=UUID(dto.workspace_id), folder_id=folder_id)
        saved_table = await self.table_repo.save(table)

        saved_cols = []
        if dto.columns:
            for col_dto in dto.columns:
                col = ColumnDefinition.create(
                    table_id=saved_table.id,
                    name=col_dto.name,
                    slug=col_dto.slug,
                    col_type=ColumnType(col_dto.col_type),
                    is_required=col_dto.is_required,
                    default_value=col_dto.default_value,
                    options=col_dto.options
                )
                saved_col = await self.col_repo.save(col)
                saved_table.add_column(saved_col)
                saved_cols.append(ColumnResponseDTO(
                    id=str(saved_col.id),
                    table_id=str(saved_col.table_id),
                    name=saved_col.name,
                    slug=saved_col.slug,
                    col_type=saved_col.col_type.value,
                    is_required=saved_col.is_required,
                    default_value=saved_col.default_value,
                    options=saved_col.options
                ))

        return TableResponseDTO(
            id=str(saved_table.id),
            name=saved_table.name,
            workspace_id=str(saved_table.workspace_id),
            folder_id=str(saved_table.folder_id) if saved_table.folder_id else None,
            columns=saved_cols
        )

class RenameTableUseCase:
    def __init__(self, table_repo: ITableRepository):
        self.table_repo = table_repo

    async def execute(self, table_id: str, dto: RenameItemDTO) -> TableResponseDTO:
        table = await self.table_repo.get_by_id(UUID(table_id))
        if not table:
            raise DamaBoxDomainException("Tabela não encontrada.", status_code=404)
        table.name = dto.name
        table.updated_at = datetime.now(timezone.utc)
        saved = await self.table_repo.save(table)
        return TableResponseDTO(
            id=str(saved.id),
            name=saved.name,
            workspace_id=str(saved.workspace_id),
            folder_id=str(saved.folder_id) if saved.folder_id else None,
            columns=[]
        )

class DeleteTableUseCase:
    def __init__(self, table_repo: ITableRepository):
        self.table_repo = table_repo

    async def execute(self, table_id: str) -> None:
        table = await self.table_repo.get_by_id(UUID(table_id))
        if not table:
            raise DamaBoxDomainException("Tabela não encontrada.", status_code=404)
        table.soft_delete()
        await self.table_repo.save(table)

class MoveTableUseCase:
    def __init__(self, table_repo: ITableRepository):
        self.table_repo = table_repo

    async def execute(self, table_id: str, dto: MoveItemDTO) -> TableResponseDTO:
        table = await self.table_repo.get_by_id(UUID(table_id))
        if not table:
            raise DamaBoxDomainException("Tabela não encontrada.", status_code=404)

        new_folder = UUID(dto.new_parent_id) if dto.new_parent_id else None
        table.folder_id = new_folder
        table.updated_at = datetime.now(timezone.utc)
        saved = await self.table_repo.save(table)
        return TableResponseDTO(
            id=str(saved.id),
            name=saved.name,
            workspace_id=str(saved.workspace_id),
            folder_id=str(saved.folder_id) if saved.folder_id else None,
            columns=[]
        )

class AddColumnUseCase:
    def __init__(self, table_repo: ITableRepository, col_repo: IColumnRepository):
        self.table_repo = table_repo
        self.col_repo = col_repo

    async def execute(self, table_id: str, dto: CreateColumnDTO) -> ColumnResponseDTO:
        table_uuid = UUID(table_id)
        table = await self.table_repo.get_by_id(table_uuid)
        if not table:
            raise DamaBoxDomainException("Tabela não encontrada.", status_code=404)

        existing_cols = await self.col_repo.list_by_table(table_uuid)
        table.columns = existing_cols

        new_col = ColumnDefinition.create(
            table_id=table_uuid,
            name=dto.name,
            slug=dto.slug,
            col_type=ColumnType(dto.col_type),
            is_required=dto.is_required,
            default_value=dto.default_value,
            options=dto.options
        )
        
        # Validará limite máximo
        table.add_column(new_col)
        saved_col = await self.col_repo.save(new_col)

        return ColumnResponseDTO(
            id=str(saved_col.id),
            table_id=str(saved_col.table_id),
            name=saved_col.name,
            slug=saved_col.slug,
            col_type=saved_col.col_type.value,
            is_required=saved_col.is_required,
            default_value=saved_col.default_value,
            options=saved_col.options
        )

class CreateRelationshipUseCase:
    def __init__(
        self,
        table_repo: ITableRepository,
        col_repo: IColumnRepository,
        rel_repo: IRelationshipRepository
    ):
        self.table_repo = table_repo
        self.col_repo = col_repo
        self.rel_repo = rel_repo

    async def execute(self, dto: CreateRelationshipDTO) -> RelationshipResponseDTO:
        source_tid = UUID(dto.source_table_id)
        target_tid = UUID(dto.target_table_id)
        
        t1 = await self.table_repo.get_by_id(source_tid)
        t2 = await self.table_repo.get_by_id(target_tid)
        if not t1 or not t2:
            raise DamaBoxDomainException("Uma ou ambas as tabelas da relação não foram encontradas.", status_code=404)

        rel = Relationship.create(
            name=dto.name,
            source_table_id=source_tid,
            source_column_id=UUID(dto.source_column_id),
            target_table_id=target_tid,
            target_column_id=UUID(dto.target_column_id),
            cardinality=Cardinality(dto.cardinality)
        )
        saved = await self.rel_repo.save(rel)
        return RelationshipResponseDTO(
            id=str(saved.id),
            name=saved.name,
            source_table_id=str(saved.source_table_id),
            source_column_id=str(saved.source_column_id),
            target_table_id=str(saved.target_table_id),
            target_column_id=str(saved.target_column_id),
            cardinality=saved.cardinality.value
        )
