from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.iam.domain.repositories import (
    IUserRepository,
    ICompanyRepository,
    IOrganizationMemberRepository,
    IRefreshTokenRepository
)
from app.modules.iam.domain.entities import User, Company, OrganizationMember, RefreshToken
from app.modules.iam.domain.value_objects import Email, RoleType
from app.modules.iam.infrastructure.orm_models import (
    UserModel,
    CompanyModel,
    OrganizationMemberModel,
    RefreshTokenModel
)

class UserSQLAlchemyRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: UserModel) -> User:
        user = User(
            email=Email(model.email),
            full_name=model.full_name,
            password_hash=model.password_hash,
            is_active=model.is_active,
            is_superuser=model.is_superuser,
            entity_id=model.id
        )
        user.created_at = model.created_at
        user.updated_at = model.updated_at
        user.is_deleted = model.is_deleted
        user.deleted_at = model.deleted_at
        return user

    def _to_model(self, entity: User, existing: Optional[UserModel] = None) -> UserModel:
        if existing:
            existing.email = str(entity.email)
            existing.full_name = entity.full_name
            existing.password_hash = entity.password_hash
            existing.is_active = entity.is_active
            existing.is_superuser = entity.is_superuser
            existing.updated_at = entity.updated_at
            existing.is_deleted = entity.is_deleted
            existing.deleted_at = entity.deleted_at
            return existing
        return UserModel(
            id=entity.id,
            email=str(entity.email),
            full_name=entity.full_name,
            password_hash=entity.password_hash,
            is_active=entity.is_active,
            is_superuser=entity.is_superuser,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at
        )

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.id == user_id, UserModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: Email) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.email == str(email), UserModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, user: User) -> User:
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        model = self._to_model(user, existing)
        if not existing:
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

class CompanySQLAlchemyRepository(ICompanyRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: CompanyModel) -> Company:
        company = Company(
            name=model.name,
            database_name=model.database_name,
            cnpj=model.cnpj,
            entity_id=model.id
        )
        company.created_at = model.created_at
        company.updated_at = model.updated_at
        company.is_deleted = model.is_deleted
        company.deleted_at = model.deleted_at
        return company

    def _to_model(self, entity: Company, existing: Optional[CompanyModel] = None) -> CompanyModel:
        if existing:
            existing.name = entity.name
            existing.database_name = entity.database_name
            existing.cnpj = entity.cnpj
            existing.updated_at = entity.updated_at
            existing.is_deleted = entity.is_deleted
            existing.deleted_at = entity.deleted_at
            return existing
        return CompanyModel(
            id=entity.id,
            name=entity.name,
            database_name=entity.database_name,
            cnpj=entity.cnpj,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            is_deleted=entity.is_deleted,
            deleted_at=entity.deleted_at
        )

    async def get_by_id(self, company_id: UUID) -> Optional[Company]:
        stmt = select(CompanyModel).where(CompanyModel.id == company_id, CompanyModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_database_name(self, db_name: str) -> Optional[Company]:
        stmt = select(CompanyModel).where(CompanyModel.database_name == db_name, CompanyModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, company: Company) -> Company:
        stmt = select(CompanyModel).where(CompanyModel.id == company.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        model = self._to_model(company, existing)
        if not existing:
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

class OrganizationMemberSQLAlchemyRepository(IOrganizationMemberRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: OrganizationMemberModel) -> OrganizationMember:
        member = OrganizationMember(
            company_id=model.company_id,
            user_id=model.user_id,
            role=RoleType(model.role),
            entity_id=model.id
        )
        member.created_at = model.created_at
        member.updated_at = model.updated_at
        member.is_deleted = model.is_deleted
        member.deleted_at = model.deleted_at
        return member

    async def get_membership(self, user_id: UUID, company_id: UUID) -> Optional[OrganizationMember]:
        stmt = select(OrganizationMemberModel).where(
            OrganizationMemberModel.user_id == user_id,
            OrganizationMemberModel.company_id == company_id,
            OrganizationMemberModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_user(self, user_id: UUID) -> List[OrganizationMember]:
        stmt = select(OrganizationMemberModel).where(
            OrganizationMemberModel.user_id == user_id,
            OrganizationMemberModel.is_deleted == False
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def save(self, member: OrganizationMember) -> OrganizationMember:
        stmt = select(OrganizationMemberModel).where(OrganizationMemberModel.id == member.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.role = member.role.value
            existing.updated_at = member.updated_at
            existing.is_deleted = member.is_deleted
            existing.deleted_at = member.deleted_at
            model = existing
        else:
            model = OrganizationMemberModel(
                id=member.id,
                company_id=member.company_id,
                user_id=member.user_id,
                role=member.role.value,
                created_at=member.created_at,
                updated_at=member.updated_at,
                is_deleted=member.is_deleted,
                deleted_at=member.deleted_at
            )
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

class RefreshTokenSQLAlchemyRepository(IRefreshTokenRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: RefreshTokenModel) -> RefreshToken:
        token = RefreshToken(
            token_hash=model.token_hash,
            user_id=model.user_id,
            company_id=model.company_id,
            expires_at=model.expires_at,
            is_revoked=model.is_revoked,
            entity_id=model.id
        )
        token.created_at = model.created_at
        token.updated_at = model.updated_at
        token.is_deleted = model.is_deleted
        return token

    async def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash, RefreshTokenModel.is_deleted == False)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, token: RefreshToken) -> RefreshToken:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.id == token.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.is_revoked = token.is_revoked
            existing.updated_at = token.updated_at
            model = existing
        else:
            model = RefreshTokenModel(
                id=token.id,
                token_hash=token.token_hash,
                user_id=token.user_id,
                company_id=token.company_id,
                expires_at=token.expires_at,
                is_revoked=token.is_revoked,
                created_at=token.created_at,
                updated_at=token.updated_at,
                is_deleted=token.is_deleted,
                deleted_at=token.deleted_at
            )
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.is_revoked == False)
            .values(is_revoked=True)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
