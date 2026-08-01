from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser
from DADOS_PARA_LANGCHAIN.services.dashboard_service import build_dashboard

router = APIRouter(
    prefix="/agente-ia",
    tags=["Agente de IA - Dashboards"],
)


class DashboardRequest(BaseModel):
    pergunta: str
    nome_usuario: str | None = None


class DashboardChartResponse(BaseModel):
    id: str
    title: str
    explanation: str
    chart_type: str
    sql: str
    image_base64: str


class DashboardResponse(BaseModel):
    charts: list[DashboardChartResponse]
    raw_plan: dict
    raw_recipe: dict


@router.post(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Gerar dashboard com IA",
    description=(
        "Recebe prompt do usuário, gera consultas SQL por Gemini + LangChain, "
        "executa cada query, monta dataframes temporários e retorna imagens "
        "de gráficos em Base64."
    ),
)
async def dashboard(
    current_user: CurrentUser,
    body: DashboardRequest,
) -> DashboardResponse:
    user_id = current_user.get("sub")
    if not user_id:
        return DashboardResponse(charts=[], raw_plan={}, raw_recipe={})

    result = await build_dashboard(user_id, body.pergunta, body.nome_usuario)
    return DashboardResponse(
        charts=result["charts"],
        raw_plan=result["raw_plan"],
        raw_recipe=result["raw_recipe"],
    )
