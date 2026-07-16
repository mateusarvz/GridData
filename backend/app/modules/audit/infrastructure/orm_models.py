from datetime import datetime, timezone
from uuid import UUID
from typing import Dict, Any
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Uuid, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.modules.catalog.infrastructure.orm_models import TenantBase

class AuditLogModel(TenantBase):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    row_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dynamic_rows.id", ondelete="CASCADE"), index=True, nullable=False)
    table_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tables_definition.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    diff: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
