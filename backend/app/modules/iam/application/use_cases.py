import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import Optional
from app.modules.iam.domain.repositories import (
    IUserRepository,
    ICompanyRepository,
    IOrganizationMemberRepository,
    IRefreshTokenRepository
)
from app.modules.iam.domain.entities import RefreshToken
from app.modules.iam.domain.value_objects import Email
from app.modules.iam.application.dto import LoginRequestDTO, TokenResponseDTO, SwitchTenantDTO
from app.core.security import verify_password, create_access_token, settings
from app.shared.exceptions import DamaBoxDomainException

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

class AuthenticateUserUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        company_repo: ICompanyRepository,
        member_repo: IOrganizationMemberRepository,
        token_repo: IRefreshTokenRepository
    ):
        self.user_repo = user_repo
        self.company_repo = company_repo
        self.member_repo = member_repo
        self.token_repo = token_repo

    async def execute(self, dto: LoginRequestDTO) -> TokenResponseDTO:
        email_vo = Email(dto.email)
        user = await self.user_repo.get_by_email(email_vo)
        
        if not user or not verify_password(dto.password, user.password_hash):
            raise DamaBoxDomainException(
                detail="Credenciais inválidas. Verifique e-mail e senha.",
                title="Falha na Autenticação",
                status_code=401
            )

        if not user.is_active:
            raise DamaBoxDomainException(
                detail="Conta de usuário inativa.",
                title="Acesso Negado",
                status_code=403
            )

        # Obter empresa padrão (primeira associação)
        memberships = await self.member_repo.list_by_user(user.id)
        company_id = None
        database_name = None
        role = None

        if memberships:
            first_member = memberships[0]
            company_id = str(first_member.company_id)
            role = first_member.role.value
            comp = await self.company_repo.get_by_id(first_member.company_id)
            if comp:
                database_name = comp.database_name

        # Gerar JWT Access Token
        jwt_payload = {
            "sub": str(user.id),
            "email": str(user.email),
            "cid": company_id,
            "db": database_name,
            "role": role
        }
        access_token = create_access_token(jwt_payload)

        # Gerar Refresh Token Opaco e salvar hash
        raw_refresh = secrets.token_urlsafe(32)
        token_hash = hash_refresh_token(raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        refresh_entity = RefreshToken(
            token_hash=token_hash,
            user_id=user.id,
            company_id=UUID(company_id) if company_id else None,
            expires_at=expires_at
        )
        await self.token_repo.save(refresh_entity)

        return TokenResponseDTO(
            access_token=access_token,
            refresh_token=raw_refresh,
            user_id=str(user.id),
            company_id=company_id,
            database_name=database_name,
            role=role
        )

class RefreshTokenUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        company_repo: ICompanyRepository,
        member_repo: IOrganizationMemberRepository,
        token_repo: IRefreshTokenRepository
    ):
        self.user_repo = user_repo
        self.company_repo = company_repo
        self.member_repo = member_repo
        self.token_repo = token_repo

    async def execute(self, raw_refresh_token: str) -> TokenResponseDTO:
        token_hash = hash_refresh_token(raw_refresh_token)
        stored_token = await self.token_repo.get_by_hash(token_hash)

        if not stored_token:
            raise DamaBoxDomainException(
                detail="Refresh token inválido.",
                title="Token Inválido",
                status_code=401
            )

        # Detecção de reuso de token revogado -> Alerta de Segurança e Revogar Todos
        if stored_token.is_revoked:
            await self.token_repo.revoke_all_for_user(stored_token.user_id)
            raise DamaBoxDomainException(
                detail="Reuso de refresh token revogado detectado. Todos os tokens foram invalidados por alerta de segurança.",
                title="Alerta de Segurança",
                status_code=401
            )

        expires_at = stored_token.expires_at if stored_token.expires_at.tzinfo else stored_token.expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise DamaBoxDomainException(
                detail="Refresh token expirado.",
                title="Token Expirado",
                status_code=401
            )

        # Revogar o token atual (Rotação)
        stored_token.revoke()
        await self.token_repo.save(stored_token)

        # Gerar novos tokens
        user = await self.user_repo.get_by_id(stored_token.user_id)
        if not user or not user.is_active:
            raise DamaBoxDomainException("Usuário inativo ou não encontrado.", status_code=401)

        company_id = str(stored_token.company_id) if stored_token.company_id else None
        database_name = None
        role = None

        if stored_token.company_id:
            comp = await self.company_repo.get_by_id(stored_token.company_id)
            if comp:
                database_name = comp.database_name
            member = await self.member_repo.get_membership(user.id, stored_token.company_id)
            if member:
                role = member.role.value

        jwt_payload = {
            "sub": str(user.id),
            "email": str(user.email),
            "cid": company_id,
            "db": database_name,
            "role": role
        }
        new_access_token = create_access_token(jwt_payload)

        new_raw_refresh = secrets.token_urlsafe(32)
        new_token_hash = hash_refresh_token(new_raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_refresh_entity = RefreshToken(
            token_hash=new_token_hash,
            user_id=user.id,
            company_id=stored_token.company_id,
            expires_at=expires_at
        )
        await self.token_repo.save(new_refresh_entity)

        return TokenResponseDTO(
            access_token=new_access_token,
            refresh_token=new_raw_refresh,
            user_id=str(user.id),
            company_id=company_id,
            database_name=database_name,
            role=role
        )

class SwitchTenantUseCase:
    def __init__(
        self,
        user_repo: IUserRepository,
        company_repo: ICompanyRepository,
        member_repo: IOrganizationMemberRepository
    ):
        self.user_repo = user_repo
        self.company_repo = company_repo
        self.member_repo = member_repo

    async def execute(self, user_id: UUID, dto: SwitchTenantDTO) -> TokenResponseDTO:
        target_cid = UUID(dto.target_company_id)
        member = await self.member_repo.get_membership(user_id, target_cid)
        
        if not member:
            raise DamaBoxDomainException(
                detail="O usuário não pertence a esta organização.",
                title="Acesso Negado à Empresa",
                status_code=403
            )

        user = await self.user_repo.get_by_id(user_id)
        comp = await self.company_repo.get_by_id(target_cid)

        if not user or not comp:
            raise DamaBoxDomainException("Dados de usuário ou empresa não encontrados.", status_code=404)

        jwt_payload = {
            "sub": str(user.id),
            "email": str(user.email),
            "cid": str(comp.id),
            "db": comp.database_name,
            "role": member.role.value
        }
        new_access_token = create_access_token(jwt_payload)

        return TokenResponseDTO(
            access_token=new_access_token,
            refresh_token="", # Switch tenant re-emite apenas JWT curto ou pode reutilizar fluxo
            user_id=str(user.id),
            company_id=str(comp.id),
            database_name=comp.database_name,
            role=member.role.value
        )
