from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CreateRowDTO(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)

class UpdateRowDTO(BaseModel):
    data: Dict[str, Any]

class RowResponseDTO(BaseModel):
    id: str
    table_id: str
    data: Dict[str, Any]
    version: int
    created_at: str
    updated_at: str

class ListRowsQueryDTO(BaseModel):
    limit: int = 50
    offset: int = 0
    filters: Optional[List[Dict[str, Any]]] = None
    sort_by: Optional[str] = None
    sort_desc: bool = False

class PaginatedRowsResponseDTO(BaseModel):
    items: List[RowResponseDTO]
    total: int
    limit: int
    offset: int
