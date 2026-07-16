from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from app.modules.iam.domain.entities import User, Company, OrganizationMember, RefreshToken
from app.modules.iam.domain.value_objects import Email

class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: Email) -> Optional[User]:
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        pass

class ICompanyRepository(ABC):
    @abstractmethod
    async def get_by_id(self, company_id: UUID) -> Optional[Company]:
        pass

    @abstractmethod
    async def get_by_database_name(self, db_name: str) -> Optional[Company]:
        pass

    @abstractmethod
    async def save(self, company: Company) -> Company:
        pass

class IOrganizationMemberRepository(ABC):
    @abstractmethod
    async def get_membership(self, user_id: UUID, company_id: UUID) -> Optional[OrganizationMember]:
        pass

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> List[OrganizationMember]:
        pass

    @abstractmethod
    async def save(self, member: OrganizationMember) -> OrganizationMember:
        pass

class IRefreshTokenRepository(ABC):
    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        pass

    @abstractmethod
    async def save(self, token: RefreshToken) -> RefreshToken:
        pass

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UUID) -> int:
        pass
