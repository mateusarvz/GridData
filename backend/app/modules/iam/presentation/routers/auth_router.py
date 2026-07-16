from uuid import UUID
from fastapi import APIRouter, Response, Cookie, Request
from app.api.deps import SystemDBSession, CurrentUser
from app.modules.iam.application.dto import LoginRequestDTO, TokenResponseDTO, SwitchTenantDTO
from app.modules.iam.application.use_cases import (
    AuthenticateUserUseCase,
    RefreshTokenUseCase,
    SwitchTenantUseCase
)
from app.modules.iam.infrastructure.repositories import (
    UserSQLAlchemyRepository,
    CompanySQLAlchemyRepository,
    OrganizationMemberSQLAlchemyRepository,
    RefreshTokenSQLAlchemyRepository
)
from app.core.config import settings
from app.shared.exceptions import DamaBoxDomainException

router = APIRouter(prefix="/auth", tags=["Authentication & IAM"])

def _set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/"
    )

@router.post("/login", response_model=TokenResponseDTO)
async def login(dto: LoginRequestDTO, session: SystemDBSession, response: Response):
    u_repo = UserSQLAlchemyRepository(session)
    c_repo = CompanySQLAlchemyRepository(session)
    m_repo = OrganizationMemberSQLAlchemyRepository(session)
    t_repo = RefreshTokenSQLAlchemyRepository(session)
    
    use_case = AuthenticateUserUseCase(u_repo, c_repo, m_repo, t_repo)
    result = await use_case.execute(dto)
    
    _set_refresh_cookie(response, result.refresh_token)
    return result

@router.post("/refresh", response_model=TokenResponseDTO)
async def refresh(session: SystemDBSession, response: Response, refresh_token: str | None = Cookie(default=None)):
    if not refresh_token:
        raise DamaBoxDomainException("Refresh token ausente no Cookie HttpOnly.", status_code=401)

    u_repo = UserSQLAlchemyRepository(session)
    c_repo = CompanySQLAlchemyRepository(session)
    m_repo = OrganizationMemberSQLAlchemyRepository(session)
    t_repo = RefreshTokenSQLAlchemyRepository(session)
    
    use_case = RefreshTokenUseCase(u_repo, c_repo, m_repo, t_repo)
    result = await use_case.execute(refresh_token)
    
    _set_refresh_cookie(response, result.refresh_token)
    return result

@router.post("/switch-tenant", response_model=TokenResponseDTO)
async def switch_tenant(dto: SwitchTenantDTO, current_user: CurrentUser, session: SystemDBSession):
    user_id = UUID(current_user["sub"])
    u_repo = UserSQLAlchemyRepository(session)
    c_repo = CompanySQLAlchemyRepository(session)
    m_repo = OrganizationMemberSQLAlchemyRepository(session)
    
    use_case = SwitchTenantUseCase(u_repo, c_repo, m_repo)
    return await use_case.execute(user_id, dto)
