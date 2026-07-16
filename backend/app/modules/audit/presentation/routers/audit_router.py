from fastapi import APIRouter, Depends
from typing import Annotated, List, Dict, Any
from pydantic import BaseModel
from app.api.deps import TenantDBSession, CurrentUser
from app.modules.audit.application.dto import InlineEditDTO, RevertDTO, AuditLogResponseDTO
from app.modules.engine.application.dto import RowResponseDTO
from app.modules.audit.application.use_cases import (
    InlineEditRowUseCase,
    GetRowHistoryUseCase,
    RevertRowUseCase
)
from app.modules.engine.infrastructure.repositories import DynamicRowSQLAlchemyRepository
from app.modules.audit.infrastructure.repositories import AuditLogSQLAlchemyRepository

router = APIRouter(prefix="", tags=["Audit Logs & Time Travel"])

class InlineEditRequest(BaseModel):
    new_data: Dict[str, Any]

class RevertRequest(BaseModel):
    target_version: int

@router.put("/rows/{row_id}/inline-edit", response_model=RowResponseDTO)
async def inline_edit_row(
    row_id: str,
    req: InlineEditRequest,
    session: TenantDBSession,
    current_user: CurrentUser
):
    row_repo = DynamicRowSQLAlchemyRepository(session)
    audit_repo = AuditLogSQLAlchemyRepository(session)
    use_case = InlineEditRowUseCase(row_repo, audit_repo)
    
    dto = InlineEditDTO(user_id=current_user.get("sub"), new_data=req.new_data) # type: ignore
    return await use_case.execute(row_id, dto)

@router.get("/rows/{row_id}/history", response_model=List[AuditLogResponseDTO])
async def get_row_history(
    row_id: str,
    session: TenantDBSession,
    _: CurrentUser
):
    audit_repo = AuditLogSQLAlchemyRepository(session)
    use_case = GetRowHistoryUseCase(audit_repo)
    return await use_case.execute(row_id)

@router.post("/rows/{row_id}/revert", response_model=RowResponseDTO)
async def revert_row(
    row_id: str,
    req: RevertRequest,
    session: TenantDBSession,
    current_user: CurrentUser
):
    row_repo = DynamicRowSQLAlchemyRepository(session)
    audit_repo = AuditLogSQLAlchemyRepository(session)
    use_case = RevertRowUseCase(row_repo, audit_repo)
    
    dto = RevertDTO(user_id=current_user.get("sub"), target_version=req.target_version) # type: ignore
    return await use_case.execute(row_id, dto)
