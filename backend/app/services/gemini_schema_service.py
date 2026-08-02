"""Serviço de inferência de schema via Gemini."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.data_masking_service import is_sensitive_col

logger = logging.getLogger(__name__)

POSTGRES_TYPES = [
    "VARCHAR(255)", "VARCHAR(100)", "VARCHAR(50)", "TEXT",
    "INT", "BIGINT", "SMALLINT",
    "DECIMAL(10,2)", "DECIMAL(18,6)", "NUMERIC",
    "BOOLEAN", "DATE", "TIMESTAMP WITH TIME ZONE", "TIMESTAMP",
    "UUID", "JSONB", "JSON", "FLOAT", "DOUBLE PRECISION",
]

_PANDAS_TO_POSTGRES: dict[str, str] = {
    "int64": "BIGINT", "int32": "INT", "int16": "SMALLINT", "int8": "SMALLINT",
    "float64": "DOUBLE PRECISION", "float32": "FLOAT", "bool": "BOOLEAN",
    "datetime64[ns]": "TIMESTAMP WITH TIME ZONE", "datetime64[ns, UTC]": "TIMESTAMP WITH TIME ZONE",
    "object": "TEXT", "string": "TEXT", "category": "VARCHAR(255)",
}

_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "tabelas": {"type": "OBJECT"},
        "relacionamentos": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "acao": {"type": "STRING"},
                    "tabela_origem": {"type": "STRING"},
                    "coluna_origem": {"type": "STRING"},
                    "tabela_destino": {"type": "STRING"},
                    "coluna_destino": {"type": "STRING"},
                    "tipo_relacionamento": {"type": "STRING"},
                    "grau_confianca": {"type": "NUMBER"},
                    "justificativa": {"type": "STRING"},
                    "ajuste": {
                        "type": "OBJECT",
                        "properties": {
                            "tabela_origem": {"type": "STRING"},
                            "coluna_origem": {"type": "STRING"},
                            "tabela_destino": {"type": "STRING"},
                            "coluna_destino": {"type": "STRING"},
                            "tipo_relacionamento": {"type": "STRING"},
                        },
                    },
                },
                "required": [
                    "acao", "tabela_origem", "coluna_origem", "tabela_destino", "coluna_destino",
                    "tipo_relacionamento", "grau_confianca", "justificativa",
                ],
            },
        },
    },
    "required": ["tabelas", "relacionamentos"],
}


class ColumnInput(BaseModel):
    nome: str
    tipo_bruto: str
    total_linhas: int = 0
    valores_nulos: int = 0
    percentual_nulos: float = 0.0
    valores_unicos: int = 0
    percentual_unicidade: float = 0.0
    is_pk_candidate: bool = False
    exemplos_gemini: list[str] = Field(default_factory=list)


class TableSchemaInput(BaseModel):
    nome_tabela: str
    nome_arquivo: str
    table_id: str
    colunas: list[ColumnInput]


class FKCandidateInput(BaseModel):
    tabela_origem: str
    coluna_origem: str
    tabela_destino: str
    coluna_destino: str
    percentual_sobreposicao: float
    percentual_sobreposicao_inversa: float
    unica_origem: bool
    unica_destino: bool
    compatibilidade_nome: bool
    mesmo_nome: bool
    cardinalidade: str
    score: float
    valores_origem_amostra: list[str] = Field(default_factory=list)
    valores_destino_amostra: list[str] = Field(default_factory=list)
    ordem_origem: int = 0
    ordem_destino: int = 0


class ColumnSuggestion(BaseModel):
    nome: str
    tipo_sugerido: str


class RelationshipSuggestion(BaseModel):
    acao: Literal["confirma", "rejeita", "ajusta"]
    tabela_origem: str
    coluna_origem: str
    tabela_destino: str
    coluna_destino: str
    tipo_relacionamento: str
    grau_confianca: float
    justificativa: str = ""
    ajuste: dict[str, Any] | None = None


class SchemaSuggestion(BaseModel):
    tabelas: dict[str, list[ColumnSuggestion]]
    relacionamentos: list[RelationshipSuggestion]


def _fallback_type(tipo_bruto: str) -> str:
    return _PANDAS_TO_POSTGRES.get(tipo_bruto, "TEXT")


def _prefer_more_specific_type(local_type: str, gemini_type: str) -> str:
    local = (local_type or "").strip()
    gemini = (gemini_type or "").strip()
    if not gemini:
        return local or "TEXT"
    if gemini.upper() == "TEXT" and local and local.upper() != "TEXT":
        return local
    if gemini.upper() == "VARCHAR(255)" and local.upper() in {
        "DATE", "BOOLEAN", "INT", "BIGINT", "SMALLINT", "DECIMAL(10,2)",
        "DECIMAL(18,6)", "NUMERIC", "FLOAT", "DOUBLE PRECISION",
    }:
        return local
    return gemini


def _candidate_justificativa(c: FKCandidateInput) -> str:
    partes = []
    if c.compatibilidade_nome:
        partes.append(f"nome '{c.coluna_origem}' sugere FK para '{c.tabela_destino}'")
    if c.percentual_sobreposicao > 0:
        partes.append(
            f"{round(c.percentual_sobreposicao * 100)}% dos valores de '{c.coluna_origem}' existem em "
            f"'{c.tabela_destino}.{c.coluna_destino}'"
        )
    if c.unica_destino:
        partes.append("coluna destino única")
    return "; ".join(partes) or "heurística local"


def _normalizar_tipo_relacionamento(tipo: str) -> str:
    return "1:N" if tipo == "N:1" else tipo


def _build_prompt(tables: list[TableSchemaInput], fk_candidates: list[FKCandidateInput], infer_relationships: bool) -> str:
    payload = []
    for table in tables:
        colunas = []
        for col in table.colunas:
            item: dict[str, Any] = {
                "nome": col.nome,
                "tipo_bruto": col.tipo_bruto,
                "valores_unicos": col.valores_unicos,
                "percentual_unicidade": round(col.percentual_unicidade, 2),
                "percentual_nulos": round(col.percentual_nulos, 2),
                "is_pk_candidate": col.is_pk_candidate,
            }
            if col.exemplos_gemini and not is_sensitive_col(col.nome):
                item["exemplos"] = col.exemplos_gemini[:10]
            colunas.append(item)
        payload.append({"nome_tabela": table.nome_tabela, "total_colunas": len(table.colunas), "colunas": colunas})

    schema_json = json.dumps({"tabelas": payload}, ensure_ascii=False, indent=2)
    candidatos_json = json.dumps([c.model_dump() for c in fk_candidates[:20]], ensure_ascii=False, indent=2)

    if infer_relationships:
        rel_rules = """
RELACIONAMENTOS:
1. Use heurística e contexto dos candidatos.
2. Se ação for "confirma", preserve candidato.
3. Se ação for "ajusta", corrija colunas, direção ou tipo.
4. Se ação for "rejeita", omita no retorno final.
5. FK válida: valores do lado FK devem existir no lado PK.
6. Se ambos lados únicos, pode ser 1:1.
7. Se um lado único e outro repetido, use 1:N ou N:1 conforme direção.
8. Relacionamento com mesmo nome de coluna é sinal muito forte.
"""
    else:
        rel_rules = 'O campo "relacionamentos" deve vir como lista vazia [].'

    return f"""Você é especialista sênior em modelagem PostgreSQL.
Retorne APENAS JSON válido.

{rel_rules}

CANDIDATOS PRÉ-FILTRADOS PELO BACKEND:
{candidatos_json}

SCHEMA:
{schema_json}

FORMATO:
{{
  "tabelas": {{
    "nome_da_tabela": [{{"nome": "coluna", "tipo_sugerido": "BIGINT"}}]
  }},
  "relacionamentos": [
    {{
      "acao": "confirma",
      "tabela_origem": "pedidos",
      "coluna_origem": "cliente_id",
      "tabela_destino": "clientes",
      "coluna_destino": "id",
      "tipo_relacionamento": "N:1",
      "grau_confianca": 0.95,
      "justificativa": "cliente_id em pedidos aponta para clientes.id",
      "ajuste": null
    }}
  ]
}}"""


def _parse_gemini_response(response_text: str, tables: list[TableSchemaInput]) -> SchemaSuggestion:
    text = response_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
    data = json.loads(text)

    tabelas_result: dict[str, list[ColumnSuggestion]] = {}
    for table in tables:
        gemini_cols = data.get("tabelas", {}).get(table.nome_tabela, [])
        col_map = {c["nome"]: c.get("tipo_sugerido", "") for c in gemini_cols}
        sugestoes = []
        for col in table.colunas:
            local_tipo = getattr(col, "tipo_sugerido", "") or _fallback_type(col.tipo_bruto)
            tipo = _prefer_more_specific_type(local_tipo, col_map.get(col.nome) or local_tipo)
            if not any(tipo.upper().startswith(t.split("(")[0].upper()) for t in POSTGRES_TYPES):
                tipo = local_tipo
            sugestoes.append(ColumnSuggestion(nome=col.nome, tipo_sugerido=tipo))
        tabelas_result[table.nome_tabela] = sugestoes

    rels: list[RelationshipSuggestion] = []
    for rel in data.get("relacionamentos", []):
        try:
            acao = rel.get("acao", "confirma")
            if acao == "rejeita":
                continue
            ajuste = rel.get("ajuste")
            alvo = ajuste if acao == "ajusta" and isinstance(ajuste, dict) else rel
            tipo = alvo.get("tipo_relacionamento", rel.get("tipo_relacionamento", "1:N"))
            tipo = _normalizar_tipo_relacionamento(tipo)
            rels.append(
                RelationshipSuggestion(
                    acao=acao,
                    tabela_origem=alvo.get("tabela_origem", rel.get("tabela_origem", "")),
                    coluna_origem=alvo.get("coluna_origem", rel.get("coluna_origem", "")),
                    tabela_destino=alvo.get("tabela_destino", rel.get("tabela_destino", "")),
                    coluna_destino=alvo.get("coluna_destino", rel.get("coluna_destino", "")),
                    tipo_relacionamento=tipo,
                    grau_confianca=float(rel.get("grau_confianca", 0.8)),
                    justificativa=rel.get("justificativa", ""),
                    ajuste=ajuste,
                )
            )
        except (KeyError, ValueError, TypeError):
            continue

    return SchemaSuggestion(tabelas=tabelas_result, relacionamentos=rels)


def _fallback_suggestion(tables: list[TableSchemaInput], fk_candidates: list[FKCandidateInput]) -> SchemaSuggestion:
    tabelas_result = {
        table.nome_tabela: [
            ColumnSuggestion(nome=col.nome, tipo_sugerido=_fallback_type(col.tipo_bruto))
            for col in table.colunas
        ]
        for table in tables
    }

    rels = []
    for c in fk_candidates:
        rels.append(
            RelationshipSuggestion(
                acao="confirma",
                tabela_origem=c.tabela_origem,
                coluna_origem=c.coluna_origem,
                tabela_destino=c.tabela_destino,
                coluna_destino=c.coluna_destino,
                tipo_relacionamento=_normalizar_tipo_relacionamento("1:N" if c.cardinalidade == "N:1" else c.cardinalidade),
                grau_confianca=min(float(c.score), 0.99),
                justificativa=f"heurística local: {_candidate_justificativa(c)}",
                ajuste=None,
            )
        )
    return SchemaSuggestion(tabelas=tabelas_result, relacionamentos=rels)


def settings_gemini_available() -> bool:
    return bool(getattr(settings, "GEMINI_API_KEYS", []))


def _gemini_api_keys() -> list[str]:
    return getattr(settings, "GEMINI_API_KEYS", [])


async def suggest_schema(
    tables: list[TableSchemaInput],
    infer_relationships: bool,
    fk_candidates: list[FKCandidateInput] | None = None,
) -> SchemaSuggestion:
    fk_candidates = fk_candidates or []
    if not settings_gemini_available() or not tables:
        return _fallback_suggestion(tables, fk_candidates)

    prompt = _build_prompt(tables, fk_candidates, infer_relationships)
    try:
        async with httpx.AsyncClient() as client:
            for api_key in _gemini_api_keys():
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/"
                    f"models/gemini-2.0-flash:generateContent?key={api_key}"
                )
                try:
                    res = await client.post(url, json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "maxOutputTokens": 4096,
                            "temperature": 0.1,
                            "responseMimeType": "application/json",
                            "responseSchema": _RESPONSE_SCHEMA,
                        },
                    }, timeout=45.0)
                except (httpx.TimeoutException, httpx.RequestError):
                    continue

                if res.status_code != 200:
                    continue

                try:
                    data = res.json()
                except json.JSONDecodeError:
                    continue

                candidates = data.get("candidates", [])
                if not candidates:
                    continue

                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                if not text:
                    continue

                sugestao = _parse_gemini_response(text, tables)
                if infer_relationships and fk_candidates:
                    vistos = {(r.tabela_origem, r.coluna_origem, r.tabela_destino, r.coluna_destino) for r in sugestao.relacionamentos}
                    for c in fk_candidates:
                        chave = (c.tabela_origem, c.coluna_origem, c.tabela_destino, c.coluna_destino)
                        if chave in vistos or c.score < 0.6:
                            continue
                        sugestao.relacionamentos.append(
                            RelationshipSuggestion(
                                acao="confirma",
                                tabela_origem=c.tabela_origem,
                                coluna_origem=c.coluna_origem,
                                tabela_destino=c.tabela_destino,
                                coluna_destino=c.coluna_destino,
                                tipo_relacionamento="1:N" if c.cardinalidade == "N:1" else c.cardinalidade,
                                grau_confianca=min(float(c.score), 0.99),
                                justificativa=f"heurística local: {_candidate_justificativa(c)}",
                                ajuste=None,
                            )
                        )
                return sugestao

            return _fallback_suggestion(tables, fk_candidates)
    except Exception as exc:
        logger.exception("Erro Gemini schema: %s", exc)
        return _fallback_suggestion(tables, fk_candidates)


async def generate_commit_sql(prompt_context: str, fallback_sql: str) -> str:
    if not settings.GEMINI_API_KEYS:
        return fallback_sql
    prompt = f"Retorne APENAS SQL puro.\n\nContexto:\n{prompt_context}\n\nSQL base:\n{fallback_sql}"
    try:
        async with httpx.AsyncClient() as client:
            for api_key in settings.GEMINI_API_KEYS:
                try:
                    res = await client.post(
                        "https://generativelanguage.googleapis.com/v1beta/"
                        f"models/gemini-2.0-flash:generateContent?key={api_key}",
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.1},
                        },
                        timeout=60.0,
                    )
                except (httpx.TimeoutException, httpx.RequestError):
                    continue

                if res.status_code != 200:
                    continue

                try:
                    data = res.json()
                except json.JSONDecodeError:
                    continue

                candidates = data.get("candidates", [])
                if not candidates:
                    continue

                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                if text.startswith("```"):
                    text = re.sub(r"^```[a-z]*\n?", "", text)
                    text = re.sub(r"\n?```$", "", text.strip())
                return text.strip() or fallback_sql
            return fallback_sql
    except Exception:
        return fallback_sql
