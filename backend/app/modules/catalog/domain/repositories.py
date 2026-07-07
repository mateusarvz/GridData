from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from app.modules.catalog.domain.entities import (
    Workspace,
    Folder,
    TableDefinition,
    ColumnDefinition,
    Relationship
)

class IWorkspaceRepository(ABC):
    @abstractmethod
    async def get_by_id(self, workspace_id: UUID) -> Optional[Workspace]:
        pass

    @abstractmethod
    async def list_all(self) -> List[Workspace]:
        pass

    @abstractmethod
    async def save(self, workspace: Workspace) -> Workspace:
        pass

class IFolderRepository(ABC):
    @abstractmethod
    async def get_by_id(self, folder_id: UUID) -> Optional[Folder]:
        pass

    @abstractmethod
    async def list_by_workspace(self, workspace_id: UUID) -> List[Folder]:
        pass

    @abstractmethod
    async def save(self, folder: Folder) -> Folder:
        pass

class ITableRepository(ABC):
    @abstractmethod
    async def get_by_id(self, table_id: UUID) -> Optional[TableDefinition]:
        pass

    @abstractmethod
    async def list_by_workspace(self, workspace_id: UUID) -> List[TableDefinition]:
        pass

    @abstractmethod
    async def save(self, table: TableDefinition) -> TableDefinition:
        pass

class IColumnRepository(ABC):
    @abstractmethod
    async def list_by_table(self, table_id: UUID) -> List[ColumnDefinition]:
        pass

    @abstractmethod
    async def save(self, column: ColumnDefinition) -> ColumnDefinition:
        pass

class IRelationshipRepository(ABC):
    @abstractmethod
    async def list_by_table(self, table_id: UUID) -> List[Relationship]:
        pass

    @abstractmethod
    async def save(self, relationship: Relationship) -> Relationship:
        pass
