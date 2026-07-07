import pytest
from uuid import UUID
from app.modules.iam.domain.value_objects import Email, RoleType
from app.modules.iam.domain.entities import User, Company, OrganizationMember
from app.shared.exceptions import DamaBoxDomainException

def test_email_value_object_validation():
    email = Email("Davi.J@DamaBox.com ")
    assert str(email) == "davi.j@damabox.com"
    
    with pytest.raises(DamaBoxDomainException, match="Formato de e-mail inválido"):
        Email("invalid-email")

def test_user_entity_creation_and_soft_delete():
    user = User.create(
        email="dev@damabox.com",
        full_name="Davi J",
        password_hash="hashed_secret_password"
    )
    
    assert isinstance(user.id, UUID)
    assert str(user.email) == "dev@damabox.com"
    assert user.is_active is True
    assert user.is_deleted is False
    
    # Executar Soft Delete
    user.soft_delete()
    assert user.is_deleted is True
    assert user.deleted_at is not None

def test_company_and_organization_member_creation():
    company = Company.create(
        name="Empresa Dama",
        cnpj="12.345.678/0001-90",
        database_name="empresa_0001"
    )
    
    user = User.create(
        email="owner@damabox.com",
        full_name="Dono Dama",
        password_hash="hash"
    )
    
    member = OrganizationMember.create(
        company_id=company.id,
        user_id=user.id,
        role=RoleType.OWNER
    )
    
    assert member.company_id == company.id
    assert member.user_id == user.id
    assert member.role == RoleType.OWNER
