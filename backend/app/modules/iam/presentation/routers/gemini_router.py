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


class GeminiStatusResponse(BaseModel):
    connected: bool
    error: str | None = None


class GeminiChatRequest(BaseModel):
    prompt: str


class GeminiChatResponse(BaseModel):
    response: str
    error: str | None = None


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


def _refresh_schema_db_temporario(user_id: str) -> str:
    global schema_DB_temporario
    cached = _cache_get(user_id)
    if cached:
        schema_DB_temporario = cached
        return cached

    client = get_supabase_service_client()
    rows: list[dict[str, Any]] = []
    owned_tables: list[dict[str, Any]] = []

    if client is not None:
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
            user_row = getattr(public_users, "data", None) or {}
            if user_row:
                rows.append({
                    "table_schema": "public",
                    "table_name": "users",
                    "owner_user_id": user_id,
                    "columns": ["id", "email", "nome_usuario"],
                })
        except Exception:
            pass

        for table_name, owner_column in (("users_table", "user_id"), ("users_table", "users_id"), ("user_table", "user_id"), ("user_table", "users_id")):
            fetched = _query_table_rows(client, table_name, owner_column, user_id)
            if fetched:
                owned_tables = fetched
                break

        for item in owned_tables:
            nome_tabela = item.get("nome_tabela")
            if not nome_tabela:
                continue
            rows.append({
                "table_schema": "table_schema",
                "table_name": nome_tabela,
                "owner_user_id": user_id,
                "users_table_id": item.get("id"),
                "columns": list(item.get("columns", [])) if isinstance(item.get("columns"), list) else [],
            })

    schema_DB_temporario = json.dumps(
        {
            "owner_user_id": user_id,
            "tables": rows,
            "relationships": [
                {
                    "from": "public.users.id",
                    "to": "table_schema.users_table.users_id",
                    "type": "1:N",
                    "meaning": "user owns tables through users_table",
                },
                {
                    "from": "table_schema.users_table.id",
                    "to": "table_schema.*.users_table_id",
                    "type": "1:N",
                    "meaning": "every schema table belongs to one users_table row",
                },
            ],
        },
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


def _read_only_sql(sql: str) -> bool:
    normalized = sql.strip().lower()
    allowed = ("select", "with", "show", "explain")
    blocked = ("insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke")
    return normalized.startswith(allowed) and not any(word in normalized for word in blocked)


async def _run_sql(sql: str) -> str:
    if not _read_only_sql(sql):
        return "SQL bloqueado: apenas leitura permitida."

    return "SQL execucao desativada no modo rapido."


def _planner_prompt(user_prompt: str, schema_snapshot: str) -> str:
    return f"""
Atue como gerente/analista de banco de dados.
Responda em portugues natural, curto e direto, como uma pessoa falando.
Sem markdown, sem lista, sem aspas, sem crases, sem explicacao longa.
Se for listar tabelas, use frase corrida.
Se a pergunta for simples, responda em uma unica frase.
As tabelas do usuario sao somente as tabelas de table_schema ligadas ao usuario logado por users_table_id.

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
        schema_snapshot = _refresh_schema_db_temporario(str(current_user.get("sub")))
        if not schema_snapshot:
            return GeminiChatResponse(response="", error="Nao foi possivel carregar schema do usuario.")

        payload = {
            "contents": [{"parts": [{"text": _planner_prompt(dto.prompt, schema_snapshot)}]}],
            "generationConfig": {
                "maxOutputTokens": 180,
                "temperature": 0.05,
            },
        }
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

        return GeminiChatResponse(response=answer)

    except httpx.TimeoutException:
        return GeminiChatResponse(response="", error="Timeout ao falar com Gemini.")
    except Exception as exc:
        return GeminiChatResponse(response="", error=str(exc))
