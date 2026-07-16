import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.modules.iam.infrastructure.orm_models import Base
from app.modules.iam.infrastructure.repositories import (
    UserSQLAlchemyRepository,
    CompanySQLAlchemyRepository,
    OrganizationMemberSQLAlchemyRepository,
    RefreshTokenSQLAlchemyRepository
)
from app.modules.iam.domain.entities import User, Company, OrganizationMember
from app.modules.iam.domain.value_objects import RoleType
from app.modules.iam.application.dto import LoginRequestDTO, SwitchTenantDTO
from app.modules.iam.application.use_cases import (
    AuthenticateUserUseCase,
    RefreshTokenUseCase,
    SwitchTenantUseCase
)
from app.core.security import get_password_hash
from app.shared.exceptions import DamaBoxDomainException

@pytest_asyncio.fixture
async def session_and_repos():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # Setup dados de teste
        user_repo = UserSQLAlchemyRepository(session)
        comp_repo = CompanySQLAlchemyRepository(session)
        member_repo = OrganizationMemberSQLAlchemyRepository(session)
        token_repo = RefreshTokenSQLAlchemyRepository(session)
        
        user = User.create("test@dama.com", "Test User", get_password_hash("Senha@123"))
        await user_repo.save(user)
        
        company = Company.create("Empresa Teste", "empresa_teste", "11111111111111")
        await comp_repo.save(company)
        
        member = OrganizationMember.create(company.id, user.id, RoleType.ADMIN)
        await member_repo.save(member)
        
        yield (session, user_repo, comp_repo, member_repo, token_repo, user, company)
    await engine.dispose()

@pytest.mark.asyncio
async def test_authenticate_user_use_case(session_and_repos):
    _, user_repo, comp_repo, member_repo, token_repo, user, company = session_and_repos
    
    use_case = AuthenticateUserUseCase(user_repo, comp_repo, member_repo, token_repo)
    
    # Login válido
    dto = LoginRequestDTO(email="test@dama.com", password="Senha@123")
    response = await use_case.execute(dto)
    
    assert response.access_token is not None
    assert response.refresh_token is not None
    assert response.user_id == str(user.id)
    assert response.company_id == str(company.id)
    assert response.database_name == "empresa_teste"
    
    # Login com senha errada
    with pytest.raises(DamaBoxDomainException, match="Credenciais inválidas"):
        await use_case.execute(LoginRequestDTO(email="test@dama.com", password="errada"))

@pytest.mark.asyncio
async def test_refresh_token_use_case_rotation_and_reuse(session_and_repos):
    _, user_repo, comp_repo, member_repo, token_repo, user, company = session_and_repos
    
    auth_uc = AuthenticateUserUseCase(user_repo, comp_repo, member_repo, token_repo)
    login_res = await auth_uc.execute(LoginRequestDTO(email="test@dama.com", password="Senha@123"))
    
    refresh_uc = RefreshTokenUseCase(user_repo, comp_repo, member_repo, token_repo)
    
    # Rotacionar com token válido
    new_tokens = await refresh_uc.execute(login_res.refresh_token)
    assert new_tokens.access_token is not None
    assert new_tokens.refresh_token != login_res.refresh_token
    
    # Tentar usar o token ANTIGO (já revogado pela rotação) deve disparar alerta de reuso e erro
    with pytest.raises(DamaBoxDomainException, match="alerta de segurança"):
        await refresh_uc.execute(login_res.refresh_token)

@pytest.mark.asyncio
async def test_switch_tenant_use_case(session_and_repos):
    _, user_repo, comp_repo, member_repo, token_repo, user, company = session_and_repos
    
    # Criar segunda empresa sem membro
    comp_2 = Company.create("Empresa Alheia", "empresa_alheia")
    await comp_repo.save(comp_2)
    
    switch_uc = SwitchTenantUseCase(user_repo, comp_repo, member_repo)
    
    # Trocar para empresa que NÃO é membro deve falhar
    with pytest.raises(DamaBoxDomainException, match="não pertence a esta organização"):
        await switch_uc.execute(user.id, SwitchTenantDTO(target_company_id=str(comp_2.id)))
