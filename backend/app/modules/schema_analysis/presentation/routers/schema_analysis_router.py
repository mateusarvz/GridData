"""
Router de schema analysis — 7 endpoints.

Autenticação: user_id recebido via body (mesmo padrão do supabase_login_router).
Isolamento: validado explicitamente em cada use case antes de qualquer operação Supabase.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Annotated

from app.modules.schema_analysis.application.dto import (
    CriarSessaoResponse,
    InferirSchemaRequest,
    InferirSchemaResponse,
    GetSessaoResponse,
    EditarColunaRequest,
    EditarColunaResponse,
    CriarRelacionamentoRequest,
    CriarRelacionamentoResponse,
    EditarRelacionamentoRequest,
    EditarRelacionamentoResponse,
    CommitSessaoRequest,
    CommitSessaoResponse,
)
from app.modules.schema_analysis.application.use_cases import (
    CriarSessaoUseCase,
    InferirSchemaUseCase,
    GetSessaoUseCase,
    EditarColunaUseCase,
    CriarRelacionamentoUseCase,
    EditarRelacionamentoUseCase,
    CommitSessaoUseCase,
)

router = APIRouter(prefix="", tags=["Schema Analysis"])


# ---------------------------------------------------------------------------
# Endpoint 1: POST /sessions
# Recebe arquivos + user_id (form field), cria sessão, extrai schema bruto
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=CriarSessaoResponse)
async def criar_sessao(
    user_id: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id é obrigatório.")
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")

    file_contents: list[tuple[str, bytes]] = []
    for upload in files:
        content = await upload.read()
        file_contents.append((upload.filename or "arquivo", content))

    use_case = CriarSessaoUseCase()
    result = await use_case.execute(user_id, file_contents)

    if not result.ok:
        raise HTTPException(status_code=500, detail=result.error)
    return result


# ---------------------------------------------------------------------------
# Endpoint 2: POST /sessions/{session_id}/infer
# Chama Gemini para sugerir tipos e relacionamentos
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/infer", response_model=InferirSchemaResponse)
async def inferir_schema(session_id: str, dto: InferirSchemaRequest):
    if not dto.user_id:
        raise HTTPException(status_code=400, detail="user_id é obrigatório.")

    use_case = InferirSchemaUseCase()
    result = await use_case.execute(dto.user_id, session_id)

    if not result.ok:
        status = 403 if "acesso negado" in (result.error or "").lower() else 500
        raise HTTPException(status_code=status, detail=result.error)
    return result


# ---------------------------------------------------------------------------
# Endpoint 3: GET /sessions/{session_id}?user_id=xxx
# Retorna sessão completa para renderizar a UI de revisão
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}", response_model=GetSessaoResponse)
async def get_sessao(session_id: str, user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id é obrigatório.")

    use_case = GetSessaoUseCase()
    result = await use_case.execute(user_id, session_id)

    if not result.ok:
        status = 403 if "acesso negado" in (result.error or "").lower() else 404
        raise HTTPException(status_code=status, detail=result.error)
    return result


# ---------------------------------------------------------------------------
# Endpoint 4: PATCH /sessions/{session_id}/tables/{table_id}/columns/{column_name}
# Edita tipo de uma coluna específica
# ---------------------------------------------------------------------------

@router.patch(
    "/sessions/{session_id}/tables/{table_id}/columns/{column_name}",
    response_model=EditarColunaResponse,
)
async def editar_coluna(
    session_id: str,
    table_id: str,
    column_name: str,
    dto: EditarColunaRequest,
):
    if not dto.user_id:
        raise HTTPException(status_code=400, detail="user_id é obrigatório.")
    if not dto.novo_tipo:
        raise HTTPException(status_code=400, detail="novo_tipo é obrigatório.")

    use_case = EditarColunaUseCase()
    result = await use_case.execute(dto.user_id, session_id, table_id, column_name, dto.novo_tipo)

    if not result.ok:
        status = 403 if "acesso negado" in (result.error or "").lower() else 400
        raise HTTPException(status_code=status, detail=result.error)
    return result


# ---------------------------------------------------------------------------
# Endpoint 5: POST /sessions/{session_id}/relationships
# Cria relacionamento manual
# ---------------------------------------------------------------------------

@router.post(
    "/sessions/{session_id}/relationships",
    response_model=CriarRelacionamentoResponse,
)
async def criar_relacionamento(session_id: str, dto: CriarRelacionamentoRequest):
    if not dto.user_id:
        raise HTTPException(status_code=400, detail="user_id é obrigatório.")

    use_case = CriarRelacionamentoUseCase()
    result = await use_case.execute(
        dto.user_id, session_id,
        dto.tabela_origem_id, dto.coluna_origem,
        dto.tabela_destino_id, dto.coluna_destino,
        dto.tipo_relacionamento,
    )

    if not result.ok:
        status = 403 if "acesso negado" in (result.error or "").lower() else 400
        raise HTTPException(status_code=status, detail=result.error)
    return result


# ---------------------------------------------------------------------------
# Endpoint 6: PATCH /sessions/{session_id}/relationships/{relationship_id}
# Edita ou remove (aprovado=false) um relacionamento
# ---------------------------------------------------------------------------

@router.patch(
    "/sessions/{session_id}/relationships/{relationship_id}",
    response_model=EditarRelacionamentoResponse,
)
async def editar_relacionamento(
    session_id: str,
    relationship_id: str,
    dto: EditarRelacionamentoRequest,
):
    if not dto.user_id:
        raise HTTPException(status_code=400, detail="user_id é obrigatório.")

    use_case = EditarRelacionamentoUseCase()
    result = await use_case.execute(
        dto.user_id, session_id, relationship_id,
        dto.aprovado, dto.tipo_relacionamento,
    )

    if not result.ok:
        status = 403 if "acesso negado" in (result.error or "").lower() else 400
        raise HTTPException(status_code=status, detail=result.error)
    return result


# ---------------------------------------------------------------------------
# Endpoint 7: POST /sessions/{session_id}/commit
# Gera DDL, registra metadados e limpa staging
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/commit", response_model=CommitSessaoResponse)
async def commit_sessao(session_id: str, dto: CommitSessaoRequest):
    if not dto.user_id:
        raise HTTPException(status_code=400, detail="user_id é obrigatório.")

    use_case = CommitSessaoUseCase()
    result = await use_case.execute(dto.user_id, session_id)

    if not result.ok:
        status = 403 if "acesso negado" in (result.error or "").lower() else 500
        raise HTTPException(status_code=status, detail=result.error)
    return result
