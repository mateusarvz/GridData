"""
Serviço de inferência de schema via Gemini.

Fluxo de segurança:
- Nunca envia valores de colunas sensíveis ao Gemini.
- Envia apenas metadados + estatísticas + amostras mascaradas.
- Candidatos FK pré-calculados pelo backend chegam como contexto.
- Fallback gracioso: se Gemini falhar, usa candidatos FK diretamente.
"""

import re
import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.services.data_masking_service import is_sensitive_col

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

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

# Schema de resposta obrigatório — garante que 'relacionamentos' NUNCA é omitido
_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "tabelas": {"type": "OBJECT"},
        "relacionamentos": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "tabela_origem": {"type": "STRING"},
                    "coluna_origem": {"type": "STRING"},
                    "tabela_destino": {"type": "STRING"},
                    "coluna_destino": {"type": "STRING"},
                    "tipo_relacionamento": {"type": "STRING"},
                    "grau_confianca": {"type": "NUMBER"},
                    "justificativa": {"type": "STRING"},
                },
                "required": [
                    "tabela_origem", "coluna_origem",
                    "tabela_destino", "coluna_destino",
                    "tipo_relacionamento", "grau_confianca", "justificativa",
                ],
            },
        },
    },
    "required": ["tabelas", "relacionamentos"],
}


# ---------------------------------------------------------------------------
# Modelos de entrada
# ---------------------------------------------------------------------------

class ColumnInput(BaseModel):
    nome: str
    tipo_bruto: str
    total_linhas: int = 0
    # Estatísticas descritivas
    valores_nulos: int = 0
    percentual_nulos: float = 0.0
    valores_unicos: int = 0
    percentual_unicidade: float = 0.0
    is_pk_candidate: bool = False
    # Amostras mascaradas para o Gemini (max 8)
    exemplos_gemini: list[str] = []


class TableSchemaInput(BaseModel):
    nome_tabela: str
    nome_arquivo: str
    table_id: str  # ID interno — não exposto ao Gemini
    colunas: list[ColumnInput]


class FKCandidateInput(BaseModel):
    """Candidato FK pré-calculado pelo backend, enviado como contexto ao Gemini."""
    tabela_origem: str
    coluna_origem: str
    tabela_destino: str
    coluna_destino: str
    percentual_sobreposicao: float
    compatibilidade_nome: bool
    score: float


# ---------------------------------------------------------------------------
# Modelos de saída
# ---------------------------------------------------------------------------

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
    justificativa: str = ""


class SchemaSuggestion(BaseModel):
    tabelas: dict[str, list[ColumnSuggestion]]
    relacionamentos: list[RelationshipSuggestion]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _fallback_type(tipo_bruto: str) -> str:
    return _PANDAS_TO_POSTGRES.get(tipo_bruto, "TEXT")


def _normalizar_confianca(rel: RelationshipSuggestion) -> float:
    """
    1.0 só quando colunas iguais.
    Qualquer par diferente fica abaixo de 100%.
    """
    if rel.coluna_origem.lower() != rel.coluna_destino.lower():
        return min(float(rel.grau_confianca), 0.99)
    return min(float(rel.grau_confianca), 1.0)


def _build_prompt(
    tables: list[TableSchemaInput],
    fk_candidates: list[FKCandidateInput],
    infer_relationships: bool,
) -> str:
    """
    Monta prompt rico com schema + estatísticas + candidatos FK pré-calculados.
    Todas as tabelas da sessão em uma única chamada.
    """
    # Serializar schema com estatísticas
    tabelas_payload = []
    for table in tables:
        colunas = []
        for col in table.colunas:
            col_entry: dict[str, Any] = {
                "nome": col.nome,
                "tipo_bruto": col.tipo_bruto,
                "valores_unicos": col.valores_unicos,
                "percentual_unicidade": round(col.percentual_unicidade, 2),
                "percentual_nulos": round(col.percentual_nulos, 2),
                "is_pk_candidate": col.is_pk_candidate,
            }
            if col.exemplos_gemini and not is_sensitive_col(col.nome):
                col_entry["exemplos"] = col.exemplos_gemini[:8]
            colunas.append(col_entry)

        tabelas_payload.append({
            "nome_tabela": table.nome_tabela,
            "total_colunas": len(table.colunas),
            "colunas": colunas,
        })

    schema_json = json.dumps({"tabelas": tabelas_payload}, ensure_ascii=False, indent=2)

    # Instrução de relacionamentos
    if not infer_relationships:
        rel_section = 'O campo "relacionamentos" deve ser uma lista vazia [].\nNÃO sugira relacionamentos.'
    else:
        candidatos_ctx = ""
        if fk_candidates:
            cands = []
            for c in fk_candidates[:10]:  # Top 10 candidatos
                cands.append(
                    f'  - {c.tabela_origem}.{c.coluna_origem} → {c.tabela_destino}.{c.coluna_destino}'
                    f' (sobreposição de valores: {round(c.percentual_sobreposicao * 100)}%,'
                    f' nome compatível: {c.compatibilidade_nome}, score: {c.score})'
                )
            candidatos_ctx = (
                "\n\nCANDIDATOS A FK PRÉ-CALCULADOS PELO BACKEND:\n"
                "Os seguintes pares foram identificados por heurística de nome + sobreposição de valores.\n"
                "Valide-os, ajuste tipo de relacionamento e grau_confianca, e inclua todos com evidência plausível:\n"
                + "\n".join(cands)
            )

        rel_section = f"""IDENTIFICAÇÃO DE RELACIONAMENTOS FK — OBRIGATÓRIO:

Raciocine passo a passo (internamente, não inclua o raciocínio na resposta):
1. Para cada tabela, identifique a coluna mais provável de ser PK
   (coluna "id", alta unicidade [is_pk_candidate=true], sem nulos).
2. Para cada outra tabela, procure colunas cujo nome sugira referência à entidade
   (padrões: <entidade>_id, id_<entidade>, cod_<entidade>).
3. Se os exemplos de valores mostram sobreposição (valores FK contidos nos valores PK),
   isso é evidência forte — inclua o relacionamento mesmo sem certeza total.
4. NUNCA omita relacionamento plausível só por incerteza parcial — use grau_confianca
   para expressar isso (0.5–0.7 = plausível, 0.8–0.95 = forte evidência, 0.95+ = certeza).
5. grau_confianca mínimo para incluir: 0.4. Abaixo disso, omita.
6. Tipo padrão para FK simples: "1:N". Use "1:1" se unicidade de ambos ≈ 1.0.
   Use "N:N" apenas se houver tabela de junção explícita.
7. Preencha "justificativa" com uma frase curta explicando a evidência
   (ex: "cliente_id em pedidos contém 95% dos valores de id em clientes").
{candidatos_ctx}"""

    return f"""Você é um especialista sênior em modelagem de banco de dados PostgreSQL.
Analise o schema abaixo e retorne APENAS JSON válido, sem texto adicional.

REGRAS OBRIGATÓRIAS:
1. Responda SOMENTE com JSON, sem markdown, sem texto antes ou depois.
2. Para cada coluna, sugira o tipo PostgreSQL mais adequado baseado no nome, tipo bruto,
   unicidade e exemplos de valores.
3. Tipos válidos: VARCHAR(n), TEXT, INT, BIGINT, SMALLINT, DECIMAL(p,s), NUMERIC,
   BOOLEAN, DATE, TIMESTAMP WITH TIME ZONE, UUID, JSONB, FLOAT, DOUBLE PRECISION.
4. Você NÃO tem acesso aos dados reais das linhas — trabalhe com metadados e estatísticas.
5. A chave "relacionamentos" DEVE SEMPRE estar presente na resposta, mesmo que vazia [].

{rel_section}

FORMATO DE RESPOSTA (JSON puro, sem markdown):
{{
  "tabelas": {{
    "nome_da_tabela": [
      {{"nome": "nome_coluna", "tipo_sugerido": "BIGINT"}}
    ]
  }},
  "relacionamentos": [
    {{
      "tabela_origem": "pedidos",
      "coluna_origem": "cliente_id",
      "tabela_destino": "clientes",
      "coluna_destino": "id",
      "tipo_relacionamento": "1:N",
      "grau_confianca": 0.95,
      "justificativa": "cliente_id em pedidos segue padrão FK; 100% dos valores presentes em clientes.id"
    }}
  ]
}}

SCHEMA PARA ANÁLISE:
{schema_json}"""


def _parse_gemini_response(
    response_text: str,
    tables: list[TableSchemaInput],
) -> SchemaSuggestion:
    """Parseia resposta JSON do Gemini com fallback por coluna."""
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
            tipo = col_map.get(col.nome) or _fallback_type(col.tipo_bruto)
            # Valida tipo retornado
            if not any(tipo.upper().startswith(t.split("(")[0].upper()) for t in POSTGRES_TYPES):
                tipo = _fallback_type(col.tipo_bruto)
            sugestoes.append(ColumnSuggestion(nome=col.nome, tipo_sugerido=tipo))

        tabelas_result[table.nome_tabela] = sugestoes

    relacionamentos: list[RelationshipSuggestion] = []
    for rel in data.get("relacionamentos", []):
        try:
            sugestao_rel = RelationshipSuggestion(
                tabela_origem=rel["tabela_origem"],
                coluna_origem=rel["coluna_origem"],
                tabela_destino=rel["tabela_destino"],
                coluna_destino=rel["coluna_destino"],
                tipo_relacionamento=rel.get("tipo_relacionamento", "1:N"),
                grau_confianca=float(rel.get("grau_confianca", 0.8)),
                justificativa=rel.get("justificativa", ""),
            )
            sugestao_rel.grau_confianca = _normalizar_confianca(sugestao_rel)
            relacionamentos.append(sugestao_rel)
        except (KeyError, ValueError):
            continue

    return SchemaSuggestion(tabelas=tabelas_result, relacionamentos=relacionamentos)


def _fallback_suggestion(
    tables: list[TableSchemaInput],
    fk_candidates: list[FKCandidateInput],
) -> SchemaSuggestion:
    """
    Fallback quando Gemini está indisponível.
    Tipos: mapeamento pandas→Postgres.
    Relacionamentos: candidatos FK pré-calculados convertidos diretamente.
    """
    tabelas_result: dict[str, list[ColumnSuggestion]] = {}
    for table in tables:
        tabelas_result[table.nome_tabela] = [
            ColumnSuggestion(nome=col.nome, tipo_sugerido=_fallback_type(col.tipo_bruto))
            for col in table.colunas
        ]

    rels: list[RelationshipSuggestion] = []
    for c in fk_candidates:
        conf = min(float(c.score), 1.0 if c.coluna_origem.lower() == c.coluna_destino.lower() else 0.99)
        rels.append(RelationshipSuggestion(
            tabela_origem=c.tabela_origem,
            coluna_origem=c.coluna_origem,
            tabela_destino=c.tabela_destino,
            coluna_destino=c.coluna_destino,
            tipo_relacionamento="1:N",
            grau_confianca=conf,
            justificativa=f"detectado por heurística local: {c.justificativa_fallback() if hasattr(c, 'justificativa_fallback') else 'nome + sobreposição de valores'}",
        ))

    return SchemaSuggestion(tabelas=tabelas_result, relacionamentos=rels)


# ---------------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------------

async def suggest_schema(
    tables: list[TableSchemaInput],
    infer_relationships: bool,
    fk_candidates: list[FKCandidateInput] | None = None,
) -> SchemaSuggestion:
    """
    Envia schema enriquecido ao Gemini (todas as tabelas em uma única chamada)
    e retorna tipos sugeridos + relacionamentos com justificativa.

    Args:
        tables: Schema de todas as tabelas da sessão com estatísticas.
        infer_relationships: True se há múltiplos arquivos na sessão.
        fk_candidates: Candidatos FK pré-calculados pelo backend (contexto extra para Gemini).

    Em caso de falha do Gemini:
        - Tipos: mapeamento local pandas→Postgres.
        - Relacionamentos: fk_candidates convertidos diretamente (score como confiança).
    """
    if fk_candidates is None:
        fk_candidates = []

    if not settings.GEMINI_API_KEY or not tables:
        return _fallback_suggestion(tables, fk_candidates)

    prompt = _build_prompt(tables, fk_candidates, infer_relationships)

    try:
        async with httpx.AsyncClient() as client:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
            )
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 4096,
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                    "responseSchema": _RESPONSE_SCHEMA,
                },
            }
            res = await client.post(url, json=body, timeout=45.0)

            if res.status_code != 200:
                logger.warning(
                    "Gemini schema API retornou %s — fallback com %d candidatos FK",
                    res.status_code, len(fk_candidates),
                )
                return _fallback_suggestion(tables, fk_candidates)

            data = res.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return _fallback_suggestion(tables, fk_candidates)

            text = (
                candidates[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )

            sugestao = _parse_gemini_response(text, tables)

            # Complementar com candidatos FK que o Gemini não detectou
            if infer_relationships and fk_candidates:
                rels_gemini = {
                    (r.tabela_origem, r.coluna_origem, r.tabela_destino)
                    for r in sugestao.relacionamentos
                }
                for c in fk_candidates:
                    chave = (c.tabela_origem, c.coluna_origem, c.tabela_destino)
                    if chave not in rels_gemini and c.score >= 0.6:
                        sugestao.relacionamentos.append(RelationshipSuggestion(
                            tabela_origem=c.tabela_origem,
                            coluna_origem=c.coluna_origem,
                            tabela_destino=c.tabela_destino,
                            coluna_destino=c.coluna_destino,
                            tipo_relacionamento="1:N",
                            grau_confianca=min(float(c.score), 1.0 if c.coluna_origem.lower() == c.coluna_destino.lower() else 0.99),
                            justificativa=f"detectado por heurística local (Gemini não retornou): {c.justificativa_fallback() if hasattr(c, 'justificativa_fallback') else ''}",
                        ))

            logger.info(
                "Gemini schema: %d tabelas, %d relacionamentos sugeridos",
                len(tables), len(sugestao.relacionamentos),
            )
            return sugestao

    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning("Timeout/erro Gemini: %s — fallback com %d FK candidates", exc, len(fk_candidates))
        return _fallback_suggestion(tables, fk_candidates)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("Erro ao parsear resposta Gemini: %s — fallback", exc)
        return _fallback_suggestion(tables, fk_candidates)
    except Exception as exc:
        logger.exception("Erro inesperado no Gemini schema service: %s", exc)
        return _fallback_suggestion(tables, fk_candidates)


async def generate_commit_sql(prompt_context: str, fallback_sql: str) -> str:
    """
    Segunda chamada ao Gemini no momento do commit.
    Retorna SQL completo para criar tabelas em table_schema, inserir dados e FKs.
    Se Gemini falhar, retorna fallback_sql determinístico do backend.
    """
    if not settings.GEMINI_API_KEY:
        return fallback_sql

    prompt = f"""Você é especialista em PostgreSQL e Supabase.
Retorne APENAS SQL puro (sem markdown, sem explicações).
Objetivo:
- Usar schema table_schema.
- Garantir coluna row_id UUID PRIMARY KEY DEFAULT gen_random_uuid() e users_table_id em cada tabela de dados.
- Preservar todas colunas do CSV, inclusive id.
- Inserir todos os dados e relacionamentos informados.
- SQL idempotente (IF NOT EXISTS quando aplicável).
- Só criar FK quando coluna destino tiver PK ou UNIQUE.

Contexto:
{prompt_context}

SQL base (fallback do backend). Melhore somente se necessário sem quebrar regras:
{fallback_sql}
"""

    try:
        async with httpx.AsyncClient() as client:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
            )
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 8192,
                    "temperature": 0.1,
                },
            }
            res = await client.post(url, json=body, timeout=60.0)
            if res.status_code != 200:
                logger.warning("Gemini commit SQL API retornou %s; usando fallback.", res.status_code)
                return fallback_sql

            data = res.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return fallback_sql

            text = (
                candidates[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
            if not text:
                return fallback_sql

            if text.startswith("```"):
                text = re.sub(r"^```[a-z]*\n?", "", text)
                text = re.sub(r"\n?```$", "", text.strip())

            return text.strip() or fallback_sql
    except Exception as exc:
        logger.warning("Falha ao gerar SQL de commit via Gemini: %s", exc)
        return fallback_sql
