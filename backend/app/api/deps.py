from typing import AsyncGenerator, Annotated, Dict, Any
from fastapi import Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import db_manager, get_system_session
from app.core.security import decode_access_token
from app.shared.exceptions import DamaBoxDomainException

# Dependência para o banco administrativo 'sistema'
SystemDBSession = Annotated[AsyncSession, Depends(get_system_session)]

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)]
) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise DamaBoxDomainException("Token de autenticação ausente ou malformatado.", status_code=401)
    
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as e:
        raise DamaBoxDomainException(str(e), status_code=401)
    
    # Injetar metadados no state da request para roteamento de tenant
    request.state.user_id = payload.get("sub")
    request.state.company_id = payload.get("cid")
    request.state.tenant_db_name = payload.get("db", "empresa_0001")
    request.state.role = payload.get("role")
    
    return payload

CurrentUser = Annotated[Dict[str, Any], Depends(get_current_user)]

async def get_tenant_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Obtém uma sessão do banco de dados do Tenant ativo.
    O nome do banco (ex: 'empresa_0001') deve ser injetado em request.state.tenant_db_name pelo middleware de autenticação.
    """
    tenant_db_name = getattr(request.state, "tenant_db_name", "empresa_0001")
    session_maker = db_manager.get_tenant_session_maker(tenant_db_name)
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

TenantDBSession = Annotated[AsyncSession, Depends(get_tenant_session)]
