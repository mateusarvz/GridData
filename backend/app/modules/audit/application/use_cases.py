from uuid import UUID
from typing import List
from app.modules.engine.domain.repositories import IDynamicRowRepository
from app.modules.audit.domain.repositories import IAuditLogRepository
from app.modules.audit.domain.entities import AuditLog
from app.modules.audit.domain.value_objects import AuditAction, ChangeDiff
from app.modules.audit.application.dto import InlineEditDTO, RevertDTO, AuditLogResponseDTO
from app.modules.engine.application.dto import RowResponseDTO
from app.shared.exceptions import DamaBoxDomainException

def _to_audit_dto(log: AuditLog) -> AuditLogResponseDTO:
    return AuditLogResponseDTO(
        id=str(log.id),
        row_id=str(log.row_id),
        table_id=str(log.table_id),
        user_id=str(log.user_id),
        action=log.action.value,
        version=log.version,
        diff=log.diff,
        created_at=log.created_at.isoformat()
    )

def _to_row_dto(row) -> RowResponseDTO:
    return RowResponseDTO(
        id=str(row.id),
        table_id=str(row.table_id),
        data=row.data,
        version=row.version,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat()
    )

class InlineEditRowUseCase:
    def __init__(self, row_repo: IDynamicRowRepository, audit_repo: IAuditLogRepository):
        self.row_repo = row_repo
        self.audit_repo = audit_repo

    async def execute(self, row_id: str, dto: InlineEditDTO) -> RowResponseDTO:
        r_uuid = UUID(row_id)
        row = await self.row_repo.get_by_id(r_uuid)
        if not row:
            raise DamaBoxDomainException("Registro não encontrado para edição inline.", status_code=404)

        old_data = row.data.copy()
        new_data = dto.new_data

        # Computar diff
        diff_vo = ChangeDiff.compute(old_data, new_data)
        if not diff_vo.changes:
            return _to_row_dto(row)

        # Atualizar linha (incrementa versão)
        row.update_data(new_data)
        saved_row = await self.row_repo.save(row)

        # Salvar log de auditoria
        audit_log = AuditLog.create(
            row_id=saved_row.id,
            table_id=saved_row.table_id,
            user_id=UUID(dto.user_id),
            action=AuditAction.UPDATE,
            version=saved_row.version,
            diff=diff_vo.changes
        )
        await self.audit_repo.save(audit_log)

        return _to_row_dto(saved_row)

class GetRowHistoryUseCase:
    def __init__(self, audit_repo: IAuditLogRepository):
        self.audit_repo = audit_repo

    async def execute(self, row_id: str) -> List[AuditLogResponseDTO]:
        r_uuid = UUID(row_id)
        logs = await self.audit_repo.list_by_row(r_uuid)
        return [_to_audit_dto(log) for log in logs]

class RevertRowUseCase:
    def __init__(self, row_repo: IDynamicRowRepository, audit_repo: IAuditLogRepository):
        self.row_repo = row_repo
        self.audit_repo = audit_repo

    async def execute(self, row_id: str, dto: RevertDTO) -> RowResponseDTO:
        r_uuid = UUID(row_id)
        row = await self.row_repo.get_by_id(r_uuid)
        if not row:
            raise DamaBoxDomainException("Registro não encontrado para reversão.", status_code=404)

        # Buscar o log de auditoria da versão que queremos reverter
        target_log = await self.audit_repo.get_by_row_and_version(r_uuid, dto.target_version)
        if not target_log:
            raise DamaBoxDomainException(f"Log de auditoria para a versão {dto.target_version} não encontrado.", status_code=404)

        # Aplicar reversão do diff dessa versão sobre os dados atuais
        reverted_data = ChangeDiff.revert(row.data, target_log.diff)
        
        # Calcular o diff da reversão para salvar no novo log
        revert_diff = ChangeDiff.compute(row.data, reverted_data)

        # Atualizar linha
        row.update_data(reverted_data)
        saved_row = await self.row_repo.save(row)

        # Salvar log com ação REVERT
        audit_log = AuditLog.create(
            row_id=saved_row.id,
            table_id=saved_row.table_id,
            user_id=UUID(dto.user_id),
            action=AuditAction.REVERT,
            version=saved_row.version,
            diff=revert_diff.changes
        )
        await self.audit_repo.save(audit_log)

        return _to_row_dto(saved_row)
