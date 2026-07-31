"""
Router: /agente-ia — LangChain-accessible schema structure endpoint.

SECURITY:
- user_id is extracted from the JWT via CurrentUser, NEVER from client input.
- All dynamic table queries validate against the users_table whitelist.
- This endpoint returns structural metadata ONLY — no row data.
- Row data is only accessed when the SQL Agent executes a generated query
  against a read-only, user-restricted database connection at runtime.

Implementation note:
  SchemaRepository uses the Supabase service client (REST/RPC) internally.
  No SQLAlchemy session is required here.
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser
from DADOS_PARA_LANGCHAIN.models.estrutura_dto import (
    EstruturaAcessivelResponse,
)
from DADOS_PARA_LANGCHAIN.services.schema_repository import (
    SchemaRepository,
)
from DADOS_PARA_LANGCHAIN.services.agent_context_builder import (
    build_agent_schema_context,
)

router = APIRouter(
    prefix="/agente-ia",
    tags=["Agente de IA - LangChain"],
)


@router.get(
    "/estrutura-acessivel",
    response_model=EstruturaAcessivelResponse,
    summary="Estrutura de tabelas que o LangChain consultará",
    description=(
        "Busca metadados, colunas e relacionamentos das tabelas do usuário "
        "autenticado no schema table_schema. NÃO retorna dados de linha — "
        "apenas estrutura. Os dados reais só são acessados quando o SQL Agent "
        "executar uma query gerada contra uma conexão restrita ao usuário."
    ),
)
async def estrutura_acessivel(
    current_user: CurrentUser,
) -> EstruturaAcessivelResponse:
    """
    Retrieve the full LangChain-accessible structure for the authenticated user.

    1. Extracts user_id from the JWT (never from client input).
    2. Fetches all tables from table_schema.users_table for this user via Supabase REST.
    3. For each table, queries information_schema via the execute_sql_readonly RPC.
    4. Returns JSON with names, types, and relationships — NO row data.
    """
    # SECURITY: user_id vem do JWT, nunca do client
    user_id = current_user.get("sub")
    if not user_id:
        return EstruturaAcessivelResponse(tabelas=[])

    repo = SchemaRepository()
    tabelas = await repo.build_full_schema(user_id)

    return EstruturaAcessivelResponse(tabelas=tabelas)


@router.get(
    "/contexto-agente",
    summary="Contexto textual para o SQL Agent (DDL simplificado)",
    description=(
        "Versão em texto puro do schema, formatada como DDL simplificado "
        "para injeção direta no prompt do SQL Agent. Sem dados de linha."
    ),
)
async def contexto_agente(
    current_user: CurrentUser,
) -> dict:
    """
    Generate DDL-like text with the database structure for the user.

    Useful for debugging and previewing what will be injected into the
    LangChain SQL Agent prompt.
    """
    user_id = current_user.get("sub")
    if not user_id:
        return {"contexto": "-- Usuário não autenticado.", "total_tabelas": 0}

    contexto = await build_agent_schema_context(user_id)
    total_tabelas = contexto.count("CREATE TABLE")

    return {
        "contexto": contexto,
        "total_tabelas": total_tabelas,
    }
