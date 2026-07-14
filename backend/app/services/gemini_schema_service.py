"""
Serviço de inferência de schema via Gemini.

Recebe metadados de colunas (NUNCA dados de linhas reais),
retorna tipos Postgres sugeridos e relacionamentos entre tabelas.

Regras de segurança:
- Nunca envia valores reais de colunas sensíveis (cpf, email, telefone, etc.)
- Prefere enviar apenas nome + tipo bruto; exemplos só quando necessário
- Fallback gracioso: falha do Gemini não quebra o fluxo
"""

import re
import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# Regex de colunas sensíveis — exemplos de valores são omitidos
_SENSITIVE_PATTERN = re.compile(
    r"(cpf|cnpj|rg|senha|password|secret|token|credit_card|cartao|telefone|"
    r"phone|celular|email|e_mail|ssn|cep|endereco|address|nascimento|birth)",
    re.IGNORECASE,
)

# Tipos Postgres válidos que o Gemini pode sugerir
POSTGRES_TYPES = [
    "VARCHAR(255)", "VARCHAR(100)", "VARCHAR(50)", "TEXT",
    "INT", "BIGINT", "SMALLINT",
    "DECIMAL(10,2)", "DECIMAL(18,6)", "NUMERIC",
    "BOOLEAN",
    "DATE", "TIMESTAMP WITH TIME ZONE", "TIMESTAMP",
    "UUID",
    "JSONB", "JSON",
    "FLOAT", "DOUBLE PRECISION",
]

# Mapeamento rápido de tipo pandas → Postgres (fallback sem Gemini)
_PANDAS_TO_POSTGRES: dict[str, str] = {
    "int64": "BIGINT",
    "int32": "INT",
    "int16": "SMALLINT",
    "int8": "SMALLINT",
    "float64": "DOUBLE PRECISION",
    "float32": "FLOAT",
    "bool": "BOOLEAN",
    "datetime64[ns]": "TIMESTAMP WITH TIME ZONE",
    "datetime64[ns, UTC]": "TIMESTAMP WITH TIME ZONE",
    "object": "TEXT",
    "string": "TEXT",
    "category": "VARCHAR(255)",
}


class ColumnInput(BaseModel):
    nome: str
    tipo_bruto: str
    total_linhas: int = 0
    exemplos: list[Any] = []  # só preenchido para colunas não-sensíveis


class TableSchemaInput(BaseModel):
    nome_tabela: str
    nome_arquivo: str
    table_id: str  # ID interno da sessão, não exposto ao Gemini
    colunas: list[ColumnInput]


class ColumnSuggestion(BaseModel):
    nome: str
    tipo_sugerido: str


class RelationshipSuggestion(BaseModel):
    tabela_origem: str
    coluna_origem: str
    tabela_destino: str
    coluna_destino: str
    tipo_relacionamento: str  # '1:1' | '1:N' | 'N:N'
    grau_confianca: float


class SchemaSuggestion(BaseModel):
    tabelas: dict[str, list[ColumnSuggestion]]  # nome_tabela → sugestões de colunas
    relacionamentos: list[RelationshipSuggestion]


def _is_sensitive(column_name: str) -> bool:
    return bool(_SENSITIVE_PATTERN.search(column_name))


def _fallback_type(tipo_bruto: str) -> str:
    return _PANDAS_TO_POSTGRES.get(tipo_bruto, "TEXT")


def _build_payload(tables: list[TableSchemaInput], infer_relationships: bool) -> dict:
    """Monta payload seguro para o Gemini — apenas metadados, nunca dados reais."""
    tabelas_payload = []
    for table in tables:
        colunas = []
        for col in table.colunas:
            col_entry: dict[str, Any] = {
                "nome": col.nome,
                "tipo_bruto": col.tipo_bruto,
            }
            # Exemplos só para colunas não-sensíveis
            if col.exemplos and not _is_sensitive(col.nome):
                col_entry["exemplos"] = col.exemplos[:3]
            colunas.append(col_entry)

        tabelas_payload.append({
            "nome_tabela": table.nome_tabela,
            "total_colunas": len(table.colunas),
            "colunas": colunas,
        })

    return {"tabelas": tabelas_payload, "inferir_relacionamentos": infer_relationships}


def _build_prompt(payload: dict, infer_relationships: bool) -> str:
    schema_json = json.dumps(payload, ensure_ascii=False, indent=2)

    rel_instruction = ""
    if infer_relationships:
        rel_instruction = """
Para cada par de tabelas, identifique colunas que sugerem chave estrangeira
(ex: coluna 'usuario_id' em uma tabela e 'id' em 'usuarios').
Retorne relacionamentos apenas quando houver evidência clara no nome das colunas.
Tipo de relacionamento: '1:1', '1:N' ou 'N:N'.
grau_confianca: valor entre 0.0 e 1.0 indicando sua certeza.
"""
    else:
        rel_instruction = """
NÃO sugira relacionamentos, chaves primárias nem chaves estrangeiras.
O campo 'relacionamentos' deve ser uma lista vazia [].
"""

    return f"""Você é um especialista em banco de dados PostgreSQL.
Analise o schema abaixo e retorne APENAS JSON válido, sem texto adicional.

REGRAS OBRIGATÓRIAS:
1. Responda SOMENTE com JSON, sem markdown, sem texto antes ou depois.
2. Para cada coluna, sugira o tipo PostgreSQL mais adequado baseado no nome e tipo bruto.
3. Tipos válidos: VARCHAR(n), TEXT, INT, BIGINT, SMALLINT, DECIMAL(p,s), NUMERIC,
   BOOLEAN, DATE, TIMESTAMP WITH TIME ZONE, UUID, JSONB, FLOAT, DOUBLE PRECISION.
4. Você NÃO tem acesso aos dados reais das linhas — trabalhe apenas com metadados.
5. Não presuma nem invente dados que não foram fornecidos.
{rel_instruction}

FORMAT O DE RESPOSTA (JSON puro):
{{
  "tabelas": {{
    "nome_da_tabela": [
      {{"nome": "nome_coluna", "tipo_sugerido": "VARCHAR(255)"}}
    ]
  }},
  "relacionamentos": [
    {{
      "tabela_origem": "...",
      "coluna_origem": "...",
      "tabela_destino": "...",
      "coluna_destino": "...",
      "tipo_relacionamento": "1:N",
      "grau_confianca": 0.9
    }}
  ]
}}

SCHEMA PARA ANÁLISE:
{schema_json}"""


def _parse_gemini_response(
    response_text: str,
    tables: list[TableSchemaInput],
) -> SchemaSuggestion:
    """Parseia resposta JSON do Gemini com fallback por tabela."""
    # Remove markdown code blocks se presentes
    text = response_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    data = json.loads(text)

    tabelas_result: dict[str, list[ColumnSuggestion]] = {}
    for table in tables:
        gemini_cols = data.get("tabelas", {}).get(table.nome_tabela, [])
        col_map = {c["nome"]: c.get("tipo_sugerido", "") for c in gemini_cols}

        sugestoes = []
        for col in table.colunas:
            tipo = col_map.get(col.nome) or _fallback_type(col.tipo_bruto)
            # Valida que o tipo retornado é aceitável
            if not any(tipo.upper().startswith(t.split("(")[0].upper()) for t in POSTGRES_TYPES):
                tipo = _fallback_type(col.tipo_bruto)
            sugestoes.append(ColumnSuggestion(nome=col.nome, tipo_sugerido=tipo))

        tabelas_result[table.nome_tabela] = sugestoes

    relacionamentos = []
    for rel in data.get("relacionamentos", []):
        try:
            relacionamentos.append(RelationshipSuggestion(
                tabela_origem=rel["tabela_origem"],
                coluna_origem=rel["coluna_origem"],
                tabela_destino=rel["tabela_destino"],
                coluna_destino=rel["coluna_destino"],
                tipo_relacionamento=rel.get("tipo_relacionamento", "1:N"),
                grau_confianca=float(rel.get("grau_confianca", 0.8)),
            ))
        except (KeyError, ValueError):
            continue  # Relacionamento malformado — ignora

    return SchemaSuggestion(tabelas=tabelas_result, relacionamentos=relacionamentos)


def _fallback_suggestion(tables: list[TableSchemaInput]) -> SchemaSuggestion:
    """Retorna sugestão baseada só no mapeamento local, sem Gemini."""
    tabelas_result: dict[str, list[ColumnSuggestion]] = {}
    for table in tables:
        tabelas_result[table.nome_tabela] = [
            ColumnSuggestion(nome=col.nome, tipo_sugerido=_fallback_type(col.tipo_bruto))
            for col in table.colunas
        ]
    return SchemaSuggestion(tabelas=tabelas_result, relacionamentos=[])


async def suggest_schema(
    tables: list[TableSchemaInput],
    infer_relationships: bool,
) -> SchemaSuggestion:
    """
    Envia metadados de schema ao Gemini e retorna sugestões de tipos e relacionamentos.

    Em caso de falha (API indisponível, timeout, JSON inválido),
    retorna sugestão de fallback baseada no mapeamento pandas→Postgres local.
    """
    if not settings.GEMINI_API_KEY or not tables:
        return _fallback_suggestion(tables)

    payload = _build_payload(tables, infer_relationships)
    prompt = _build_prompt(payload, infer_relationships)

    try:
        async with httpx.AsyncClient() as client:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
            )
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 2048,
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                },
            }
            res = await client.post(url, json=body, timeout=30.0)

            if res.status_code != 200:
                logger.warning("Gemini schema API retornou %s — usando fallback", res.status_code)
                return _fallback_suggestion(tables)

            data = res.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return _fallback_suggestion(tables)

            text = (
                candidates[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )

            return _parse_gemini_response(text, tables)

    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning("Timeout/erro na chamada ao Gemini: %s — usando fallback", exc)
        return _fallback_suggestion(tables)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("Erro ao parsear resposta Gemini: %s — usando fallback", exc)
        return _fallback_suggestion(tables)
    except Exception as exc:
        logger.exception("Erro inesperado no Gemini schema service: %s", exc)
        return _fallback_suggestion(tables)
