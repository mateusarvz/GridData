from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class CreateWorkspaceDTO(BaseModel):
    name: str
    owner_id: str

class WorkspaceResponseDTO(BaseModel):
    id: str
    name: str
    owner_id: str

class CreateFolderDTO(BaseModel):
    name: str
    workspace_id: str
    parent_id: Optional[str] = None

class FolderResponseDTO(BaseModel):
    id: str
    name: str
    workspace_id: str
    parent_id: Optional[str] = None

class CreateColumnDTO(BaseModel):
    name: str
    slug: str
    col_type: str
    is_required: bool = False
    default_value: Optional[Any] = None
    options: Optional[Dict[str, Any]] = None

class ColumnResponseDTO(BaseModel):
    id: str
    table_id: str
    name: str
    slug: str
    col_type: str
    is_required: bool
    default_value: Optional[Any] = None
    options: Dict[str, Any]

class CreateTableDTO(BaseModel):
    name: str
    workspace_id: str
    folder_id: Optional[str] = None
    columns: Optional[List[CreateColumnDTO]] = None

class TableResponseDTO(BaseModel):
    id: str
    name: str
    workspace_id: str
    folder_id: Optional[str] = None
    columns: List[ColumnResponseDTO] = []

class CreateRelationshipDTO(BaseModel):
    name: str
    source_table_id: str
    source_column_id: str
    target_table_id: str
    target_column_id: str
    cardinality: str

class RelationshipResponseDTO(BaseModel):
    id: str
    name: str
    source_table_id: str
    source_column_id: str
    target_table_id: str
    target_column_id: str
    cardinality: str
