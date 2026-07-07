from uuid import UUID
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.modules.iam.domain.entities import BaseDomainEntity, generate_uuidv7
from app.modules.engine.domain.value_objects import RowData

class DynamicRow(BaseDomainEntity):
    def __init__(
        self,
        table_id: UUID,
        data: Dict[str, Any],
        version: int = 1,
        entity_id: Optional[UUID] = None
    ):
        super().__init__(entity_id)
        self.table_id = table_id
        # Validar payload de dados via Value Object
        self._row_data = RowData(data)
        self.version = version

    @property
    def data(self) -> Dict[str, Any]:
        return self._row_data.value

    @classmethod
    def create(cls, table_id: UUID, data: Dict[str, Any]) -> "DynamicRow":
        return cls(table_id=table_id, data=data, version=1)

    def update_data(self, new_data: Dict[str, Any]):
        self._row_data = RowData(new_data)
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
