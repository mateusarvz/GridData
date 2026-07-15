from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.domain.repositories import IAuditLogRepository
from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.domain.value_objects import AuditAction
from app.modules.audit.infrastructure.orm_models import AuditLogModel

class AuditLogSQLAlchemyRepository(IAuditLogRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: AuditLogModel) -> AuditLog:
        log = AuditLog(
            row_id=model.row_id,
            table_id=model.table_id,
            user_id=model.user_id,
            action=AuditAction(model.action),
            version=model.version,
            diff=model.diff,
            entity_id=model.id
        )
        log.created_at = model.created_at
        log.updated_at = model.updated_at
        log.is_deleted = model.is_deleted
        return log

    async def save(self, log: AuditLog) -> AuditLog:
        stmt = select(AuditLogModel).where(AuditLogModel.id == log.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.action = log.action.value
            existing.version = log.version
            existing.diff = log.diff
            existing.updated_at = log.updated_at
            model = existing
        else:
            model = AuditLogModel(
                id=log.id,
                row_id=log.row_id,
                table_id=log.table_id,
                user_id=log.user_id,
                action=log.action.value,
                version=log.version,
                diff=log.diff,
                created_at=log.created_at,
                updated_at=log.updated_at,
                is_deleted=log.is_deleted
            )
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, log_id: UUID) -> Optional[AuditLog]:
        stmt = select(AuditLogModel).where(AuditLogModel.id == log_id, AuditLogModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_row(self, row_id: UUID) -> List[AuditLog]:
        stmt = select(AuditLogModel).where(
            AuditLogModel.row_id == row_id,
            AuditLogModel.is_deleted == False
        ).order_by(desc(AuditLogModel.version))
        result = await self.session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_row_and_version(self, row_id: UUID, version: int) -> Optional[AuditLog]:
        stmt = select(AuditLogModel).where(
            AuditLogModel.row_id == row_id,
            AuditLogModel.version == version,
            AuditLogModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None
