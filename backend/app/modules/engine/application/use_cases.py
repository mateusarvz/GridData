from uuid import UUID
from typing import List
from app.modules.engine.domain.repositories import IDynamicRowRepository
from app.modules.catalog.domain.repositories import ITableRepository
from app.modules.engine.domain.entities import DynamicRow
from app.modules.engine.application.dto import (
    CreateRowDTO,
    UpdateRowDTO,
    RowResponseDTO,
    ListRowsQueryDTO,
    PaginatedRowsResponseDTO
)
from app.shared.exceptions import DamaBoxDomainException

def _to_dto(row: DynamicRow) -> RowResponseDTO:
    return RowResponseDTO(
        id=str(row.id),
        table_id=str(row.table_id),
        data=row.data,
        version=row.version,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat()
    )

class CreateRowUseCase:
    def __init__(self, table_repo: ITableRepository, row_repo: IDynamicRowRepository):
        self.table_repo = table_repo
        self.row_repo = row_repo

    async def execute(self, table_id: str, dto: CreateRowDTO) -> RowResponseDTO:
        t_uuid = UUID(table_id)
        table = await self.table_repo.get_by_id(t_uuid)
        if not table:
            raise DamaBoxDomainException("Tabela não encontrada.", status_code=404)

        row = DynamicRow.create(table_id=t_uuid, data=dto.data)
        saved = await self.row_repo.save(row)
        return _to_dto(saved)

class UpdateRowUseCase:
    def __init__(self, row_repo: IDynamicRowRepository):
        self.row_repo = row_repo

    async def execute(self, row_id: str, dto: UpdateRowDTO) -> RowResponseDTO:
        r_uuid = UUID(row_id)
        row = await self.row_repo.get_by_id(r_uuid)
        if not row:
            raise DamaBoxDomainException("Registro não encontrado.", status_code=404)

        row.update_data(dto.data)
        saved = await self.row_repo.save(row)
        return _to_dto(saved)

class ListRowsUseCase:
    def __init__(self, row_repo: IDynamicRowRepository):
        self.row_repo = row_repo

    async def execute(self, table_id: str, dto: ListRowsQueryDTO) -> PaginatedRowsResponseDTO:
        t_uuid = UUID(table_id)
        rows, total = await self.row_repo.list_by_table(
            table_id=t_uuid,
            limit=dto.limit,
            offset=dto.offset,
            filters=dto.filters,
            sort_by=dto.sort_by,
            sort_desc=dto.sort_desc
        )
        return PaginatedRowsResponseDTO(
            items=[_to_dto(r) for r in rows],
            total=total,
            limit=dto.limit,
            offset=dto.offset
        )

class DeleteRowUseCase:
    def __init__(self, row_repo: IDynamicRowRepository):
        self.row_repo = row_repo

    async def execute(self, row_id: str) -> bool:
        r_uuid = UUID(row_id)
        deleted = await self.row_repo.delete(r_uuid)
        if not deleted:
            raise DamaBoxDomainException("Registro não encontrado para exclusão.", status_code=404)
        return True
