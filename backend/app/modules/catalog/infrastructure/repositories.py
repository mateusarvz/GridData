from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
from app.modules.catalog.infrastructure.orm_models import (
    WorkspaceModel,
    FolderModel,
    TableModel,
    ColumnModel,
    RelationshipModel
)

class WorkspaceSQLAlchemyRepository(IWorkspaceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: WorkspaceModel) -> Workspace:
        ws = Workspace(name=model.name, owner_id=model.owner_id, entity_id=model.id)
        ws.created_at = model.created_at
        ws.updated_at = model.updated_at
        ws.is_deleted = model.is_deleted
        return ws

    async def get_by_id(self, workspace_id: UUID) -> Optional[Workspace]:
        stmt = select(WorkspaceModel).where(WorkspaceModel.id == workspace_id, WorkspaceModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> List[Workspace]:
        stmt = select(WorkspaceModel).where(WorkspaceModel.is_deleted == False)
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_owner(self, owner_id: UUID) -> List[Workspace]:
        stmt = select(WorkspaceModel).where(
            WorkspaceModel.owner_id == owner_id,
            WorkspaceModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, workspace: Workspace) -> Workspace:
        stmt = select(WorkspaceModel).where(WorkspaceModel.id == workspace.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = workspace.name
            existing.owner_id = workspace.owner_id
            existing.updated_at = workspace.updated_at
            existing.is_deleted = workspace.is_deleted
            model = existing
        else:
            model = WorkspaceModel(
                id=workspace.id,
                name=workspace.name,
                owner_id=workspace.owner_id,
                created_at=workspace.created_at,
                updated_at=workspace.updated_at,
                is_deleted=workspace.is_deleted
            )
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

class FolderSQLAlchemyRepository(IFolderRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: FolderModel) -> Folder:
        f = Folder(name=model.name, workspace_id=model.workspace_id, parent_id=model.parent_id, entity_id=model.id)
        f.created_at = model.created_at
        f.updated_at = model.updated_at
        f.is_deleted = model.is_deleted
        return f

    async def get_by_id(self, folder_id: UUID) -> Optional[Folder]:
        stmt = select(FolderModel).where(FolderModel.id == folder_id, FolderModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_workspace(self, workspace_id: UUID) -> List[Folder]:
        stmt = select(FolderModel).where(FolderModel.workspace_id == workspace_id, FolderModel.is_deleted == False)
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, folder: Folder) -> Folder:
        stmt = select(FolderModel).where(FolderModel.id == folder.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = folder.name
            existing.parent_id = folder.parent_id
            existing.updated_at = folder.updated_at
            existing.is_deleted = folder.is_deleted
            model = existing
        else:
            model = FolderModel(
                id=folder.id,
                name=folder.name,
                workspace_id=folder.workspace_id,
                parent_id=folder.parent_id,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
                is_deleted=folder.is_deleted
            )
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

class TableSQLAlchemyRepository(ITableRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: TableModel) -> TableDefinition:
        t = TableDefinition(name=model.name, workspace_id=model.workspace_id, folder_id=model.folder_id, entity_id=model.id)
        t.created_at = model.created_at
        t.updated_at = model.updated_at
        t.is_deleted = model.is_deleted
        return t

    async def get_by_id(self, table_id: UUID) -> Optional[TableDefinition]:
        stmt = select(TableModel).where(TableModel.id == table_id, TableModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_workspace(self, workspace_id: UUID) -> List[TableDefinition]:
        stmt = select(TableModel).where(TableModel.workspace_id == workspace_id, TableModel.is_deleted == False)
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, table: TableDefinition) -> TableDefinition:
        stmt = select(TableModel).where(TableModel.id == table.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = table.name
            existing.folder_id = table.folder_id
            existing.updated_at = table.updated_at
            existing.is_deleted = table.is_deleted
            model = existing
        else:
            model = TableModel(
                id=table.id,
                name=table.name,
                workspace_id=table.workspace_id,
                folder_id=table.folder_id,
                created_at=table.created_at,
                updated_at=table.updated_at,
                is_deleted=table.is_deleted
            )
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

class ColumnSQLAlchemyRepository(IColumnRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: ColumnModel) -> ColumnDefinition:
        c = ColumnDefinition(
            table_id=model.table_id,
            name=model.name,
            slug=model.slug,
            col_type=ColumnType(model.col_type),
            is_required=model.is_required,
            default_value=model.default_value,
            options=model.options,
            entity_id=model.id
        )
        c.created_at = model.created_at
        c.updated_at = model.updated_at
        c.is_deleted = model.is_deleted
        return c

    async def list_by_table(self, table_id: UUID) -> List[ColumnDefinition]:
        stmt = select(ColumnModel).where(ColumnModel.table_id == table_id, ColumnModel.is_deleted == False)
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, column: ColumnDefinition) -> ColumnDefinition:
        stmt = select(ColumnModel).where(ColumnModel.id == column.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = column.name
            existing.slug = column.slug
            existing.col_type = column.col_type.value
            existing.is_required = column.is_required
            existing.default_value = column.default_value
            existing.options = column.options
            existing.updated_at = column.updated_at
            existing.is_deleted = column.is_deleted
            model = existing
        else:
            model = ColumnModel(
                id=column.id,
                table_id=column.table_id,
                name=column.name,
                slug=column.slug,
                col_type=column.col_type.value,
                is_required=column.is_required,
                default_value=column.default_value,
                options=column.options,
                created_at=column.created_at,
                updated_at=column.updated_at,
                is_deleted=column.is_deleted
            )
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

class RelationshipSQLAlchemyRepository(IRelationshipRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: RelationshipModel) -> Relationship:
        r = Relationship(
            name=model.name,
            source_table_id=model.source_table_id,
            source_column_id=model.source_column_id,
            target_table_id=model.target_table_id,
            target_column_id=model.target_column_id,
            cardinality=Cardinality(model.cardinality),
            entity_id=model.id
        )
        r.created_at = model.created_at
        r.updated_at = model.updated_at
        r.is_deleted = model.is_deleted
        return r

    async def list_by_table(self, table_id: UUID) -> List[Relationship]:
        stmt = select(RelationshipModel).where(
            (RelationshipModel.source_table_id == table_id) | (RelationshipModel.target_table_id == table_id),
            RelationshipModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, relationship: Relationship) -> Relationship:
        stmt = select(RelationshipModel).where(RelationshipModel.id == relationship.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = relationship.name
            existing.cardinality = relationship.cardinality.value
            existing.updated_at = relationship.updated_at
            existing.is_deleted = relationship.is_deleted
            model = existing
        else:
            model = RelationshipModel(
                id=relationship.id,
                name=relationship.name,
                source_table_id=relationship.source_table_id,
                source_column_id=relationship.source_column_id,
                target_table_id=relationship.target_table_id,
                target_column_id=relationship.target_column_id,
                cardinality=relationship.cardinality.value,
                created_at=relationship.created_at,
                updated_at=relationship.updated_at,
                is_deleted=relationship.is_deleted
            )
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)
