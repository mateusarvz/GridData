from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from typing import Annotated

from app.modules.data_session.application.use_cases import (
    UploadDataFilesUseCase,
    ListSessionTablesUseCase,
    GetTablePreviewUseCase,
    DeleteSessionTablesUseCase,
    ListRelatedUserTablesUseCase,
)
from app.modules.data_session.infrastructure.redis_data_session_store import RedisDataSessionStore
from app.shared.exceptions import DamaBoxDomainException

router = APIRouter(prefix="", tags=["Data Session"])

# Para efeitos de MVP, usar user_id no cabeçalho ou token em cookies não autenticados.
# Ideal: dependência CurrentUser ou Auth bearer.

async def get_current_user_id() -> str:
    # Placeholder simples: extraia user_id de um cabeçalho customizado para desenvolvimento
    # Em produção, substituir por dependência JWT / CurrentUser com autenticação real.
    return "anonymous-session"


@router.post("/data/upload")
async def upload_data_files(
    files: Annotated[list[UploadFile], File()],
    user_id: str = Depends(get_current_user_id),
):
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")

    try:
        file_contents = []
        for file in files:
            content = await file.read()
            file_contents.append((file.filename, content))

        use_case = UploadDataFilesUseCase(RedisDataSessionStore())
        result = await use_case.execute(user_id, file_contents)
        return [item.dict() for item in result]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/data/session")
async def list_session_tables(user_id: str = Depends(get_current_user_id)):
    use_case = ListSessionTablesUseCase(RedisDataSessionStore())
    result = await use_case.execute(user_id)
    return [item.dict() for item in result]


@router.get("/data/{table_id}/preview")
async def get_table_preview(
    table_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(1000, ge=1, le=1000),
    user_id: str = Depends(get_current_user_id),
):
    use_case = GetTablePreviewUseCase(RedisDataSessionStore())
    result = await use_case.execute(user_id, table_id, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Tabela não encontrada na sessão.")
    return result.dict()


@router.delete("/data/session")
async def delete_session_tables(user_id: str = Depends(get_current_user_id)):
    use_case = DeleteSessionTablesUseCase(RedisDataSessionStore())
    await use_case.execute(user_id)
    return {"ok": True}


@router.get("/data/user-tables")
async def list_user_tables(user_id: str):
    use_case = ListRelatedUserTablesUseCase()
    result = await use_case.execute(user_id)
    return result
