"""DTOs do módulo schema_analysis."""
from typing import Any
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Estruturas internas de coluna
# ---------------------------------------------------------------------------

class ColunaSchemaDTO(BaseModel):
    nome: str
    tipo_bruto: str
    tipo_sugerido: str = ""
    nulo_permitido: bool = True
    editado_pelo_usuario: bool = False


# ---------------------------------------------------------------------------
# Endpoint 1 — POST /sessions (criar sessão + upload)
# ---------------------------------------------------------------------------

class CriarSessaoRequest(BaseModel):
    user_id: str


class TabelaUploadedDTO(BaseModel):
    table_id: str
    nome_arquivo: str
    nome_tabela_sugerido: str
    total_linhas: int
    colunas: list[ColunaSchemaDTO]


class CriarSessaoResponse(BaseModel):
    ok: bool
    session_id: str | None = None
    tabelas: list[TabelaUploadedDTO] = []
    error: str | None = None


# ---------------------------------------------------------------------------
# Endpoint 2 — POST /sessions/{session_id}/infer
# ---------------------------------------------------------------------------

class InferirSchemaRequest(BaseModel):
    user_id: str


class RelacionamentoDTO(BaseModel):
    id: str | None = None
    tabela_origem_id: str
    coluna_origem: str
    tabela_destino_id: str
    coluna_destino: str
    tipo_relacionamento: str = "1:N"
    grau_confianca: float = 1.0
    origem: str = "gemini"
    aprovado: bool = True
    justificativa: str = ""
    # Nomes para exibição no frontend
    nome_tabela_origem: str = ""
    nome_tabela_destino: str = ""


class InferirSchemaResponse(BaseModel):
    ok: bool
    session_id: str | None = None
    tabelas: list[TabelaUploadedDTO] = []
    relacionamentos: list[RelacionamentoDTO] = []
    error: str | None = None
    gemini_usado: bool = False


# ---------------------------------------------------------------------------
# Endpoint 3 — GET /sessions/{session_id}
# ---------------------------------------------------------------------------

class GetSessaoResponse(BaseModel):
    ok: bool
    session_id: str | None = None
    status: str = ""
    total_arquivos: int = 0
    tabelas: list[TabelaUploadedDTO] = []
    relacionamentos: list[RelacionamentoDTO] = []
    error: str | None = None


# ---------------------------------------------------------------------------
# Endpoint 4 — PATCH /sessions/{session_id}/tables/{table_id}/columns/{column_name}
# ---------------------------------------------------------------------------

class EditarColunaRequest(BaseModel):
    user_id: str
    novo_tipo: str


class EditarNuloColunaRequest(BaseModel):
    user_id: str
    nulo_permitido: bool


class EditarColunaResponse(BaseModel):
    ok: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Endpoint 5 — POST /sessions/{session_id}/relationships
# ---------------------------------------------------------------------------

class CriarRelacionamentoRequest(BaseModel):
    user_id: str
    tabela_origem_id: str
    coluna_origem: str
    tabela_destino_id: str
    coluna_destino: str
    tipo_relacionamento: str = "1:N"


class CriarRelacionamentoResponse(BaseModel):
    ok: bool
    relacionamento: RelacionamentoDTO | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Endpoint 6 — PATCH /sessions/{session_id}/relationships/{relationship_id}
# ---------------------------------------------------------------------------

class EditarRelacionamentoRequest(BaseModel):
    user_id: str
    aprovado: bool | None = None
    tipo_relacionamento: str | None = None


class EditarRelacionamentoResponse(BaseModel):
    ok: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Endpoint 7 — POST /sessions/{session_id}/commit
# ---------------------------------------------------------------------------

class CommitSessaoRequest(BaseModel):
    user_id: str


class CommitSessaoResponse(BaseModel):
    ok: bool
    sql_gerado: str = ""
    tabelas_criadas: list[str] = []
    error: str | None = None
