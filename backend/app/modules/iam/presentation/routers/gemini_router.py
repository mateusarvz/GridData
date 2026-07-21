import json
import re
import time
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.supabase import get_supabase_service_client
from app.api.deps import CurrentUser

router = APIRouter(prefix="/gemini", tags=["Gemini Integration"])

schema_DB_temporario: str = ""
USERS_TABLE_NAMES = ("users_table", "user_table")
SCHEMA_CACHE_TTL_SECONDS = 60
_schema_cache: dict[str, dict[str, Any]] = {}
_TABLE_LIST_PATTERNS = (
    r"\bquais\s+s[aã]o\s+minhas\s+tabelas\b",
    r"\bquais\s+s[aã]o\s+as\s+minhas\s+tabelas\b",
    r"\bliste\s+minhas\s+tabelas\b",
    r"\bmostrar\s+minhas\s+tabelas\b",
    r"\bminhas\s+tabelas\b",
)
_SQL_BLOCKED_PATTERNS = (
    r"\binsert\b",
    r"\bupdate\b",
    r"\bdelete\b",
    r"\bmerge\b",
    r"\bupsert\b",
    r"\bdrop\b",
    r"\balter\b",
    r"\bcreate\b",
    r"\btruncate\b",
    r"\bgrant\b",
    r"\brevoke\b",
    r"\bcomment\b",
    r"\bcopy\b",
    r"\bcall\b",
    r"\bdo\b",
    r"\bexecute\b",
    r"\bprepare\b",
    r"\bdeallocate\b",
    r"\bvacuum\b",
    r"\banalyze\b",
    r"\breindex\b",
    r"\brefresh\b",
    r"\bcluster\b",
    r"\bdiscard\b",
    r"\bset\s+role\b",
    r"\bset\s+transaction\b",
    r"\breset\b",
)
_SQL_LEADING_OK = ("select", "with", "show", "explain", "values", "table")


class GeminiStatusResponse(BaseModel):
    connected: bool
    error: str | None = None


class GeminiChatRequest(BaseModel):
    prompt: str


class GeminiChatResponse(BaseModel):
    response: str
    error: str | None = None


class GeminiPlannerResponse(BaseModel):
    mode: str = "answer"
    sql: str | None = None
    response: str | None = None


def _gemini_url() -> str:
    return (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    )


async def _post_gemini(payload: dict[str, Any]) -> httpx.Response:
    async with httpx.AsyncClient(timeout=20.0) as client:
        return await client.post(_gemini_url(), json=payload)


def _cache_get(user_id: str) -> str | None:
    cached = _schema_cache.get(user_id)
    if not cached:
        return None
    if time.time() - cached["ts"] > SCHEMA_CACHE_TTL_SECONDS:
        return None
    return cached["value"]


def _cache_set(user_id: str, value: str) -> None:
    _schema_cache[user_id] = {"ts": time.time(), "value": value}


def _query_table_rows(client: Any, table_name: str, owner_column: str, user_id: str) -> list[dict[str, Any]]:
    try:
        response = (
            client
            .schema("table_schema")
            .from_(table_name)
            .select("*")
            .eq(owner_column, user_id)
            .execute()
        )
        data = getattr(response, "data", []) or []
        return [dict(row) for row in data]
    except Exception:
        return []


def _query_owned_tables(client: Any, user_id: str) -> list[dict[str, Any]]:
    for table_name, owner_column in (
        ("users_table", "user_id"),
        ("users_table", "users_id"),
        ("user_table", "user_id"),
        ("user_table", "users_id"),
    ):
        fetched = _query_table_rows(client, table_name, owner_column, user_id)
        if fetched:
            return fetched
    return []


def _query_table_columns(client: Any, table_name: str) -> list[str]:
    try:
        response = (
            client
            .schema("information_schema")
            .from_("columns")
            .select("column_name")
            .eq("table_schema", "table_schema")
            .eq("table_name", table_name)
            .order("ordinal_position", desc=False)
            .execute()
        )
        data = getattr(response, "data", []) or []
        return [row["column_name"] for row in data if row.get("column_name")]
    except Exception:
        return []


def _query_table_preview(client: Any, table_name: str, limit: int = 5) -> list[dict[str, Any]]:
    try:
        response = (
            client
            .schema("table_schema")
            .from_(table_name)
            .select("*")
            .limit(limit)
            .execute()
        )
        data = getattr(response, "data", []) or []
        return [dict(row) for row in data]
    except Exception:
        return []


def _query_all_owned_rows(client: Any, tables: list[dict[str, Any]], max_rows_per_table: int = 200) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    for item in tables:
        nome_tabela = item.get("table_name")
        if not nome_tabela:
            continue
        try:
            response = (
                client
                .schema("table_schema")
                .from_(nome_tabela)
                .select("*")
                .limit(max_rows_per_table)
                .execute()
            )
            data = getattr(response, "data", []) or []
            rows[nome_tabela] = [dict(row) for row in data]
        except Exception:
            rows[nome_tabela] = []
    return rows


def _build_user_table_context(client: Any, user_id: str) -> dict[str, Any]:
    public_user = {}
    try:
        public_users = (
            client
            .schema("public")
            .from_("users")
            .select("id, email, nome_usuario")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        public_user = getattr(public_users, "data", None) or {}
    except Exception:
        public_user = {}

    owned_tables = _query_owned_tables(client, user_id)
    tables: list[dict[str, Any]] = []

    for item in owned_tables:
        nome_tabela = item.get("nome_tabela")
        if not nome_tabela:
            continue
        columns = _query_table_columns(client, nome_tabela)
        tables.append(
            {
                "table_schema": "table_schema",
                "table_name": nome_tabela,
                "users_table_id": item.get("id"),
                "owner_user_id": user_id,
                "columns": columns,
                "sample_rows": _query_table_preview(client, nome_tabela, limit=5),
                "total_linhas": item.get("total_linhas"),
                "nome_origem_arquivo": item.get("nome_origem_arquivo"),
                "tipo_arquivo": item.get("tipo_arquivo"),
            }
        )

    return {
        "owner_user_id": user_id,
        "user": public_user,
        "tables": tables,
        "tables_description": [
            {
                "table_name": t["table_name"],
                "users_table_id": t["users_table_id"],
                "columns": t["columns"],
            }
            for t in tables
        ],
        "relationships": [
            {
                "from": "public.users.id",
                "to": "table_schema.users_table.user_id",
                "type": "1:N",
                "meaning": "user owns many uploaded tables",
            },
            {
                "from": "table_schema.users_table.id",
                "to": "table_schema.*.users_table_id",
                "type": "1:N",
                "meaning": "every data table belongs to one users_table row",
            },
        ],
    }


def _refresh_schema_db_temporario(user_id: str) -> str:
    global schema_DB_temporario
    cached = _cache_get(user_id)
    if cached:
        schema_DB_temporario = cached
        return cached

    client = get_supabase_service_client()
    if client is not None:
        context = _build_user_table_context(client, user_id)
    else:
        context = {"owner_user_id": user_id, "user": {}, "tables": [], "relationships": []}

    schema_DB_temporario = json.dumps(
        context,
        ensure_ascii=False,
    )
    _cache_set(user_id, schema_DB_temporario)
    return schema_DB_temporario


def _extract_json_block(text_value: str) -> dict[str, Any]:
    cleaned = text_value.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return json.loads(cleaned)


def _strip_sql_noise(sql: str) -> str:
    cleaned = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    cleaned = re.sub(r"--[^\n]*", " ", cleaned)
    cleaned = re.sub(r"'.*?'", "''", cleaned, flags=re.S)
    cleaned = re.sub(r'"[^"]*"', '""', cleaned)
    return cleaned


def _safe_non_mutating_sql(sql: str) -> bool:
    normalized = _strip_sql_noise(sql).strip().lower()
    if not normalized:
        return False
    if ";" in normalized.rstrip(";"):
        return False
    if not normalized.startswith(_SQL_LEADING_OK):
        return False
    if any(re.search(pattern, normalized) for pattern in _SQL_BLOCKED_PATTERNS):
        return False
    return True


def _table_names(context: dict[str, Any]) -> list[str]:
    tables = context.get("tables", []) or []
    return [t.get("table_name") for t in tables if t.get("table_name")]


def _find_table_for_prompt(prompt: str, table_names: list[str]) -> str | None:
    lowered = prompt.lower()
    for name in table_names:
        if name and name.lower() in lowered:
            return name
    return table_names[0] if len(table_names) == 1 else None


def _looks_like_columns_question(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(word in lowered for word in ("colunas", "coluna", "campos", "schema", "estrutura", "dentro da tabela"))


def _looks_like_contents_question(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(word in lowered for word in ("o que tem", "dentro", "conteudo", "conteúdo", "mostre", "listar", "liste", "visualize"))


def _build_fallback_sql(prompt: str, context: dict[str, Any]) -> str | None:
    table_names = _table_names(context)
    if not table_names:
        return None

    lower = prompt.lower()

    if _looks_like_columns_question(lower):
        table = _find_table_for_prompt(lower, table_names)
        if not table:
            return None
        return (
            "SELECT column_name, data_type, is_nullable, ordinal_position "
            "FROM information_schema.columns "
            f"WHERE table_schema = 'table_schema' AND table_name = '{table}' "
            "ORDER BY ordinal_position"
        )

    if _looks_like_contents_question(lower):
        parts = []
        for table in table_names:
            parts.append(
                f"SELECT '{table}' AS tabela, row_to_json(t) AS linha "
                f"FROM table_schema.{table} t"
            )
        return " UNION ALL ".join(parts)

    if any(word in lower for word in ("quant", "maior", "menor", "max", "min", "mais", "menos", "top", "ultimo", "último", "primeiro", "total")):
        table = _find_table_for_prompt(lower, table_names)
        if not table:
            return None
        cols = {c.lower() for c in (next((t.get("columns", []) for t in context.get("tables", []) if t.get("table_name") == table), []) or [])}
        if "salario" in lower or "salário" in lower:
            if "funcionario" in table.lower() or "funcionarios" in table.lower():
                return f"SELECT * FROM table_schema.{table} ORDER BY salario DESC NULLS LAST LIMIT 1"
        if ("andar" in lower or "floor" in lower) and ("apartamento" in lower or "imovel" in lower or "imóvel" in lower):
            return f"SELECT * FROM table_schema.{table} ORDER BY andar DESC NULLS LAST LIMIT 1"
        if "department" in lower or "departamento" in lower:
            if len(table_names) >= 2:
                # tenta maior ocorrência de departamentos por vínculo simples
                func_table = next((t for t in table_names if "func" in t.lower()), table)
                dept_table = next((t for t in table_names if "depart" in t.lower()), table)
                return (
                    f"WITH counts AS ("
                    f"SELECT d.*, COUNT(*) AS total_registros "
                    f"FROM table_schema.{func_table} f "
                    f"LEFT JOIN table_schema.{dept_table} d ON TRUE "
                    f"GROUP BY d.*"
                    f") SELECT * FROM counts ORDER BY total_registros DESC LIMIT 1"
                )
        if cols:
            return f"SELECT * FROM table_schema.{table} LIMIT 20"
        return f"SELECT * FROM table_schema.{table} LIMIT 20"

    table = _find_table_for_prompt(lower, table_names)
    if not table:
        return None
    return f"SELECT * FROM table_schema.{table} LIMIT 20"


def _is_table_list_question(prompt: str) -> bool:
    normalized = prompt.strip().lower()
    return any(re.search(pattern, normalized) for pattern in _TABLE_LIST_PATTERNS)


def _format_table_list(context: dict[str, Any]) -> str:
    tables = context.get("tables", []) or []
    if not tables:
        return "Voce nao tem tabelas vinculadas ao seu usuario no momento."

    names = [t.get("table_name") for t in tables if t.get("table_name")]
    if not names:
        return "Voce nao tem tabelas vinculadas ao seu usuario no momento."

    if len(names) == 1:
        return f"Sua tabela e {names[0]}."
    return "Suas tabelas sao " + ", ".join(names[:-1]) + f" e {names[-1]}."


def _build_agent_prompt(user_prompt: str, schema_context: dict[str, Any]) -> str:
    return f"""
Voce e um gerador de consultas SQL.
Sua unica saida deve ser JSON valido com:
{{
  "mode": "sql",
  "sql": "uma unica consulta SELECT ou WITH",
  "response": "frase curta opcional"
}}

Regras:
- Use somente tabelas de schema_context.tables.
- Gere sempre somente consultas de leitura.
- Nao use INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, TRUNCATE, GRANT, REVOKE, COPY, CALL, DO, EXECUTE, PREPARE, VACUUM, ANALYZE.
- Se nao conseguir inferir uma consulta perfeita, ainda assim gere uma consulta util de leitura sobre as tabelas disponiveis.
- Sempre respeite o owner_user_id.
- Responda somente com JSON valido.

schema_context:
{json.dumps(schema_context, ensure_ascii=False)[:12000]}

pergunta:
{user_prompt}
""".strip()


async def _execute_readonly_sql(client: Any, sql: str) -> list[dict[str, Any]]:
    response = client.rpc("execute_sql_readonly", {"sql_query": sql}).execute()
    data = getattr(response, "data", None)
    if data is None:
        return []
    if isinstance(data, list):
        return [dict(row) if isinstance(row, dict) else {"value": row} for row in data]
    if isinstance(data, dict):
        return [data]
    return [{"value": data}]


async def _run_sql(sql: str) -> str:
    if not _read_only_sql(sql):
        return "SQL bloqueado: apenas leitura permitida."

    return "SQL execucao desativada no modo rapido."


def _planner_prompt(user_prompt: str, schema_snapshot: str) -> str:
    return f"""
Atue como analista de banco de dados.
Responda como uma pessoa falando.
Nao invente relacao de acesso. Use apenas o JSON do schema como fonte de verdade.
As tabelas do usuario sao as entradas de schema.tables do usuario logado.

schema_DB_temporario:
{schema_snapshot[:4000]}

pergunta:
{user_prompt}
""".strip()


@router.get("/status", response_model=GeminiStatusResponse)
async def get_gemini_status():
    if not settings.GEMINI_API_KEY:
        return GeminiStatusResponse(connected=False, error="GEMINI_API_KEY nao configurada.")
    return GeminiStatusResponse(connected=True)


@router.post("/chat", response_model=GeminiChatResponse)
async def gemini_chat(dto: GeminiChatRequest, current_user: CurrentUser):
    try:
        user_id = str(current_user.get("sub"))
        schema_snapshot = _refresh_schema_db_temporario(user_id)
        if not schema_snapshot:
            return GeminiChatResponse(response="", error="Nao foi possivel carregar schema do usuario.")

        context = json.loads(schema_snapshot)
        if _is_table_list_question(dto.prompt):
            return GeminiChatResponse(response=_format_table_list(context))

        client = get_supabase_service_client()
        if client is not None:
            context["tables_rows"] = _query_all_owned_rows(client, context.get("tables", []))

        fallback_sql = _build_fallback_sql(dto.prompt, context)

        payload = {
            "contents": [{"parts": [{"text": _build_agent_prompt(dto.prompt, context)}]}],
            "generationConfig": {
                "maxOutputTokens": 320,
                "temperature": 0.0,
                "responseMimeType": "application/json",
            },
        }

        plan: dict[str, Any] | None = None
        for attempt in range(2):
            response = await _post_gemini(payload)
            if response.status_code != 200:
                return GeminiChatResponse(response="", error=f"HTTP {response.status_code}: {response.text}")

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return GeminiChatResponse(response="", error="Sem resposta do Gemini.")

            text_parts = candidates[0].get("content", {}).get("parts", [])
            answer = "".join(part.get("text", "") for part in text_parts).strip()
            if not answer:
                return GeminiChatResponse(response="", error="Resposta vazia.")

            try:
                plan = _extract_json_block(answer)
            except Exception:
                plan = None

            sql = str((plan or {}).get("sql", "")).strip()
            if plan and plan.get("mode") == "sql" and _safe_non_mutating_sql(sql):
                break

            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"""
Sua resposta anterior estava errada.
Retorne SOMENTE JSON valido com mode=sql e sql como unica consulta SELECT ou WITH.
Sem texto extra, sem markdown, sem comentarios, sem SHOW, sem EXPLAIN, sem DDL, sem DML.

pergunta:
{dto.prompt}

schema_context:
{json.dumps(context, ensure_ascii=False)[:12000]}
""".strip()
                    }]
                }],
                "generationConfig": {
                    "maxOutputTokens": 320,
                    "temperature": 0.0,
                    "responseMimeType": "application/json",
                },
            }
        else:
            if fallback_sql and _safe_non_mutating_sql(fallback_sql):
                plan = {"mode": "sql", "sql": fallback_sql, "response": "Consulta gerada pelo backend."}
            else:
                return GeminiChatResponse(response="", error="Gemini nao gerou SQL de leitura valida.")

        sql = str(plan.get("sql", "")).strip()
        if not sql and fallback_sql:
            sql = fallback_sql
        if not sql:
            return GeminiChatResponse(response="", error="Gemini pediu SQL sem consulta.")
        if not _safe_non_mutating_sql(sql):
            if fallback_sql and _safe_non_mutating_sql(fallback_sql):
                sql = fallback_sql
            else:
                return GeminiChatResponse(response="", error="Gemini gerou SQL mutante ou inseguro.")
        if client is None:
            return GeminiChatResponse(response="", error="Cliente Supabase indisponivel para executar SQL.")

        rows = await _execute_readonly_sql(client, sql)
        synth_prompt = f"""
Voce recebeu pergunta do usuario, schema e resultado SQL.
Responda de forma natural, curta e direta.
Nao mostre SQL.
Se resultado vazio, diga isso de forma objetiva.

pergunta:
{dto.prompt}

sql:
{sql}

resultado:
{json.dumps(rows, ensure_ascii=False)[:12000]}
""".strip()

        followup = await _post_gemini(
            {
                "contents": [{"parts": [{"text": synth_prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": 220,
                    "temperature": 0.1,
                },
            }
        )
        if followup.status_code != 200:
            return GeminiChatResponse(response="", error=f"HTTP {followup.status_code}: {followup.text}")

        followup_data = followup.json()
        followup_candidates = followup_data.get("candidates", [])
        if not followup_candidates:
            return GeminiChatResponse(response="", error="Sem resposta final do Gemini.")
        followup_parts = followup_candidates[0].get("content", {}).get("parts", [])
        final_answer = "".join(part.get("text", "") for part in followup_parts).strip()
        if not final_answer:
            return GeminiChatResponse(response="", error="Resposta final vazia.")
        return GeminiChatResponse(response=final_answer)

    except httpx.TimeoutException:
        return GeminiChatResponse(response="", error="Timeout ao falar com Gemini.")
    except Exception as exc:
        return GeminiChatResponse(response="", error=str(exc))
