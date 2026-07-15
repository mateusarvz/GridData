from datetime import datetime, timezone
from uuid import UUID
from typing import Dict, Any
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Uuid, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.modules.catalog.infrastructure.orm_models import TenantBase

class DynamicRowModel(TenantBase):
    __tablename__ = "dynamic_rows"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    table_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tables_definition.id", ondelete="CASCADE"), index=True, nullable=False)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
