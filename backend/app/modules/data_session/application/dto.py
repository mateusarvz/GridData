from typing import Any

from pydantic import BaseModel, Field


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


class RelatedTableSummaryDTO(BaseModel):
    table_name: str
    display_name: str
    category: str
    row_count: int | None = None
    columns_count: int | None = None
    related_to_user: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
