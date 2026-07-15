import time
import secrets
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from app.modules.iam.domain.value_objects import Email, RoleType

def generate_uuidv7() -> UUID:
    """
    Gera um UUID de versão 7 (RFC 9562) ordenável por tempo (48 bits timestamp ms + random).
    """
    timestamp_ms = int(time.time() * 1000)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    
    # 48 bits timestamp | 4 bits ver (0111) | 12 bits rand_a | 2 bits var (10) | 62 bits rand_b
    uuid_int = (timestamp_ms & 0xFFFFFFFFFFFF) << 80
    uuid_int |= (0x7 << 76)
    uuid_int |= (rand_a & 0xFFF) << 64
    uuid_int |= (0x2 << 62)
    uuid_int |= (rand_b & 0x3FFFFFFFFFFFFFFF)
    
    return UUID(int=uuid_int)

class BaseDomainEntity:
    def __init__(self, entity_id: Optional[UUID] = None):
        self.id: UUID = entity_id or generate_uuidv7()
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.is_deleted: bool = False
        self.deleted_at: Optional[datetime] = None

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

class User(BaseDomainEntity):
    def __init__(
        self,
        email: Email,
        full_name: str,
        password_hash: str,
        is_active: bool = True,
        is_superuser: bool = False,
        entity_id: Optional[UUID] = None
    ):
        super().__init__(entity_id)
        self.email = email
        self.full_name = full_name
        self.password_hash = password_hash
        self.is_active = is_active
        self.is_superuser = is_superuser

    @classmethod
    def create(cls, email: str, full_name: str, password_hash: str) -> "User":
        return cls(
            email=Email(email),
            full_name=full_name,
            password_hash=password_hash
        )

class Company(BaseDomainEntity):
    def __init__(
        self,
        name: str,
        database_name: str,
        cnpj: Optional[str] = None,
        entity_id: Optional[UUID] = None
    ):
        super().__init__(entity_id)
        self.name = name
        self.database_name = database_name
        self.cnpj = cnpj

    @classmethod
    def create(cls, name: str, database_name: str, cnpj: Optional[str] = None) -> "Company":
        return cls(name=name, database_name=database_name, cnpj=cnpj)

class OrganizationMember(BaseDomainEntity):
    def __init__(
        self,
        company_id: UUID,
        user_id: UUID,
        role: RoleType,
        entity_id: Optional[UUID] = None
    ):
        super().__init__(entity_id)
        self.company_id = company_id
        self.user_id = user_id
        self.role = role

    @classmethod
    def create(cls, company_id: UUID, user_id: UUID, role: RoleType = RoleType.MEMBER) -> "OrganizationMember":
        return cls(company_id=company_id, user_id=user_id, role=role)

class RefreshToken(BaseDomainEntity):
    def __init__(
        self,
        token_hash: str,
        user_id: UUID,
        company_id: Optional[UUID],
        expires_at: datetime,
        is_revoked: bool = False,
        entity_id: Optional[UUID] = None
    ):
        super().__init__(entity_id)
        self.token_hash = token_hash
        self.user_id = user_id
        self.company_id = company_id
        self.expires_at = expires_at
        self.is_revoked = is_revoked

    def revoke(self):
        self.is_revoked = True
        self.updated_at = datetime.now(timezone.utc)
