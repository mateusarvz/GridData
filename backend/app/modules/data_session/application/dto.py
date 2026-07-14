from typing import Any

from pydantic import BaseModel


class UploadedTableMetaDTO(BaseModel):
    table_id: str
    file_name: str
    columns: list[str]
    row_count: int
    preview: list[dict[str, Any]]


class TablePreviewDTO(BaseModel):
    table_id: str
    file_name: str
    columns: list[str]
    row_count: int
    preview: list[dict[str, Any]]
    page: int
    page_size: int
