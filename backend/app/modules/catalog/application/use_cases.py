from uuid import UUID
from typing import List
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
    RelationshipResponseDTO
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
