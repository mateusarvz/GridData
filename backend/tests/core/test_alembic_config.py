import pytest
from app.modules.iam.infrastructure.orm_models import Base
from app.modules.catalog.infrastructure.orm_models import TenantBase
from app.modules.iam.infrastructure.orm_models import UserModel, CompanyModel
from app.modules.engine.infrastructure.orm_models import DynamicRowModel
from app.modules.audit.infrastructure.orm_models import AuditLogModel

def test_system_metadata_contains_iam_tables():
    system_tables = Base.metadata.tables.keys()
    assert "users" in system_tables
    assert "companies" in system_tables
    assert "organization_members" in system_tables
    assert "refresh_tokens" in system_tables
    assert "workspaces" not in system_tables

def test_tenant_metadata_contains_catalog_engine_audit_tables():
    tenant_tables = TenantBase.metadata.tables.keys()
    assert "workspaces" in tenant_tables
    assert "folders" in tenant_tables
    assert "tables_definition" in tenant_tables
    assert "columns_definition" in tenant_tables
    assert "relationships" in tenant_tables
    assert "dynamic_rows" in tenant_tables
    assert "audit_logs" in tenant_tables
    assert "users" not in tenant_tables
