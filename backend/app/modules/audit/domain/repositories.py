from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from app.modules.audit.domain.entities import AuditLog

class IAuditLogRepository(ABC):
    @abstractmethod
    async def save(self, log: AuditLog) -> AuditLog:
        pass

    @abstractmethod
    async def get_by_id(self, log_id: UUID) -> Optional[AuditLog]:
        pass

    @abstractmethod
    async def list_by_row(self, row_id: UUID) -> List[AuditLog]:
        """
        Lista todo o histórico de logs de auditoria de um determinado registro da planilha, ordenado do mais recente para o mais antigo.
        """
        pass

    @abstractmethod
    async def get_by_row_and_version(self, row_id: UUID, version: int) -> Optional[AuditLog]:
        """
        Obtém o log de auditoria exato correspondente a uma versão específica da linha.
        """
        pass
