from uuid import UUID
from typing import Optional, Dict, Any
from app.modules.iam.domain.entities import BaseDomainEntity
from app.modules.audit.domain.value_objects import AuditAction

class AuditLog(BaseDomainEntity):
    def __init__(
        self,
        row_id: UUID,
        table_id: UUID,
        user_id: UUID,
        action: AuditAction,
        version: int,
        diff: Dict[str, Any],
        entity_id: Optional[UUID] = None
    ):
        super().__init__(entity_id)
        self.row_id = row_id
        self.table_id = table_id
        self.user_id = user_id
        self.action = action
        self.version = version
        self.diff = diff

    @classmethod
    def create(
        cls,
        row_id: UUID,
        table_id: UUID,
        user_id: UUID,
        action: AuditAction,
        version: int,
        diff: Dict[str, Any]
    ) -> "AuditLog":
        return cls(
            row_id=row_id,
            table_id=table_id,
            user_id=user_id,
            action=action,
            version=version,
            diff=diff
        )
