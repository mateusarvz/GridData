from pydantic import BaseModel
from typing import Dict, Any

class InlineEditDTO(BaseModel):
    user_id: str
    new_data: Dict[str, Any]

class RevertDTO(BaseModel):
    user_id: str
    target_version: int

class AuditLogResponseDTO(BaseModel):
    id: str
    row_id: str
    table_id: str
    user_id: str
    action: str
    version: int
    diff: Dict[str, Any]
    created_at: str
