from uuid import UUID
from typing import Optional, List, Dict, Any
from app.modules.iam.domain.entities import BaseDomainEntity, generate_uuidv7
from app.modules.catalog.domain.value_objects import ColumnType, Cardinality
from app.shared.exceptions import DamaBoxDomainException

class Workspace(BaseDomainEntity):
    def __init__(self, name: str, owner_id: UUID, entity_id: Optional[UUID] = None):
        super().__init__(entity_id)
        self.name = name
        self.owner_id = owner_id

    @classmethod
    def create(cls, name: str, owner_id: UUID) -> "Workspace":
        return cls(name=name, owner_id=owner_id)

class Folder(BaseDomainEntity):
    def __init__(self, name: str, workspace_id: UUID, parent_id: Optional[UUID] = None, entity_id: Optional[UUID] = None):
        super().__init__(entity_id)
        self.name = name
        self.workspace_id = workspace_id
        self.parent_id = parent_id

    @classmethod
    def create(cls, name: str, workspace_id: UUID, parent_id: Optional[UUID] = None) -> "Folder":
        return cls(name=name, workspace_id=workspace_id, parent_id=parent_id)

class ColumnDefinition(BaseDomainEntity):
    def __init__(
        self,
        table_id: UUID,
        name: str,
        slug: str,
        col_type: ColumnType,
        is_required: bool = False,
        default_value: Any = None,
        options: Optional[Dict[str, Any]] = None,
        entity_id: Optional[UUID] = None
    ):
        super().__init__(entity_id)
        self.table_id = table_id
        self.name = name
        self.slug = slug
        self.col_type = col_type
        self.is_required = is_required
        self.default_value = default_value
        self.options = options or {}

    @classmethod
    def create(
        cls,
        table_id: UUID,
        name: str,
        slug: str,
        col_type: ColumnType,
        is_required: bool = False,
        default_value: Any = None,
        options: Optional[Dict[str, Any]] = None
    ) -> "ColumnDefinition":
        return cls(
            table_id=table_id,
            name=name,
            slug=slug,
            col_type=col_type,
            is_required=is_required,
            default_value=default_value,
            options=options
        )

class TableDefinition(BaseDomainEntity):
    def __init__(
        self,
        name: str,
        workspace_id: UUID,
        folder_id: Optional[UUID] = None,
        columns: Optional[List[ColumnDefinition]] = None,
        entity_id: Optional[UUID] = None
    ):
        super().__init__(entity_id)
        self.name = name
        self.workspace_id = workspace_id
        self.folder_id = folder_id
        self.columns: List[ColumnDefinition] = columns or []

    @classmethod
    def create(cls, name: str, workspace_id: UUID, folder_id: Optional[UUID] = None) -> "TableDefinition":
        return cls(name=name, workspace_id=workspace_id, folder_id=folder_id)

    def add_column(self, column: ColumnDefinition):
        if len(self.columns) >= 200:
            raise DamaBoxDomainException(
                detail="Limite máximo de 200 colunas por tabela atingido.",
                title="Limite de Schema Excedido",
                status_code=400
            )
        self.columns.append(column)

class Relationship(BaseDomainEntity):
    def __init__(
        self,
        name: str,
        source_table_id: UUID,
        source_column_id: UUID,
        target_table_id: UUID,
        target_column_id: UUID,
        cardinality: Cardinality,
        entity_id: Optional[UUID] = None
    ):
        super().__init__(entity_id)
        self.name = name
        self.source_table_id = source_table_id
        self.source_column_id = source_column_id
        self.target_table_id = target_table_id
        self.target_column_id = target_column_id
        self.cardinality = cardinality

    @classmethod
    def create(
        cls,
        name: str,
        source_table_id: UUID,
        source_column_id: UUID,
        target_table_id: UUID,
        target_column_id: UUID,
        cardinality: Cardinality
    ) -> "Relationship":
        return cls(
            name=name,
            source_table_id=source_table_id,
            source_column_id=source_column_id,
            target_table_id=target_table_id,
            target_column_id=target_column_id,
            cardinality=cardinality
        )
