from fastapi import APIRouter, Depends
from typing import Annotated
from app.api.deps import TenantDBSession, CurrentUser
from app.modules.engine.application.dto import (
    CreateRowDTO,
    UpdateRowDTO,
    RowResponseDTO,
    ListRowsQueryDTO,
    PaginatedRowsResponseDTO
)
from app.modules.engine.application.use_cases import (
    CreateRowUseCase,
    UpdateRowUseCase,
    ListRowsUseCase,
    DeleteRowUseCase
)
from app.modules.engine.infrastructure.repositories import DynamicRowSQLAlchemyRepository
from app.modules.catalog.infrastructure.repositories import TableSQLAlchemyRepository

router = APIRouter(prefix="", tags=["Engine & Spreadsheet Rows"])

@router.post("/tables/{table_id}/rows", response_model=RowResponseDTO)
async def create_row(
    table_id: str,
    dto: CreateRowDTO,
    session: TenantDBSession,
    _: CurrentUser
):
    t_repo = TableSQLAlchemyRepository(session)
    r_repo = DynamicRowSQLAlchemyRepository(session)
    use_case = CreateRowUseCase(t_repo, r_repo)
    return await use_case.execute(table_id, dto)

@router.post("/tables/{table_id}/rows/query", response_model=PaginatedRowsResponseDTO)
async def query_rows(
    table_id: str,
    dto: ListRowsQueryDTO,
    session: TenantDBSession,
    _: CurrentUser
):
    r_repo = DynamicRowSQLAlchemyRepository(session)
    use_case = ListRowsUseCase(r_repo)
    return await use_case.execute(table_id, dto)

@router.patch("/rows/{row_id}", response_model=RowResponseDTO)
async def update_row(
    row_id: str,
    dto: UpdateRowDTO,
    session: TenantDBSession,
    _: CurrentUser
):
    r_repo = DynamicRowSQLAlchemyRepository(session)
    use_case = UpdateRowUseCase(r_repo)
    return await use_case.execute(row_id, dto)

@router.delete("/rows/{row_id}")
async def delete_row(
    row_id: str,
    session: TenantDBSession,
    _: CurrentUser
):
    r_repo = DynamicRowSQLAlchemyRepository(session)
    use_case = DeleteRowUseCase(r_repo)
    await use_case.execute(row_id)
    return {"status": "deleted", "row_id": row_id}
