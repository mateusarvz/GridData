from datetime import datetime, timezone
from uuid import UUID
from typing import Any, Dict
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class TenantBase(DeclarativeBase):
    pass

class WorkspaceModel(TenantBase):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class FolderModel(TenantBase):
    __tablename__ = "folders"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class TableModel(TenantBase):
    __tablename__ = "tables_definition"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    folder_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ColumnModel(TenantBase):
    __tablename__ = "columns_definition"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    table_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tables_definition.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    col_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    options: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class RelationshipModel(TenantBase):
    __tablename__ = "relationships"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_table_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tables_definition.id", ondelete="CASCADE"), index=True, nullable=False)
    source_column_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("columns_definition.id", ondelete="CASCADE"), nullable=False)
    target_table_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tables_definition.id", ondelete="CASCADE"), index=True, nullable=False)
    target_column_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("columns_definition.id", ondelete="CASCADE"), nullable=False)
    cardinality: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
