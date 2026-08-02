import asyncio
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from DADOS_PARA_LANGCHAIN.services import chat_service
from DADOS_PARA_LANGCHAIN.services.chat_service import _is_safe_select_sql, _normalize_sql_query


def test_normalize_sql_query_strips_trailing_semicolon_and_fences():
    sql = "```sql\nSELECT * FROM table_schema.users_table;\n```"

    assert _normalize_sql_query(sql) == "SELECT * FROM table_schema.users_table"


def test_is_safe_select_sql_accepts_single_select():
    assert _is_safe_select_sql("SELECT * FROM table_schema.users_table") is True


def test_is_safe_select_sql_rejects_multiple_statements():
    assert _is_safe_select_sql("SELECT * FROM table_schema.users_table; SELECT 1") is False


def test_is_safe_select_sql_rejects_write_statements():
    assert _is_safe_select_sql("INSERT INTO table_schema.users_table VALUES (1)") is False


def test_chat_with_gemini_uses_response_prompt_for_second_fallback(monkeypatch):
    class FakePromptTemplate:
        def __init__(self, name: str):
            self.name = name

        def __or__(self, other):
            return FakeChain(self, other)

    class FakeChain:
        def __init__(self, template, llm):
            self.template = template
            self.llm = llm

        async def ainvoke(self, params):
            if self.template.name == "main":
                return SimpleNamespace(content="SELECT 1 FROM table_schema.users_table ---DADOS---")
            return SimpleNamespace(content="Resposta final")

    async def fake_build_context(_user_id):
        return "CREATE TABLE table_schema.users_table (id integer)"

    async def fake_execute_sql(_sql):
        return []

    monkeypatch.setattr(chat_service, "build_agent_schema_context", fake_build_context)
    monkeypatch.setattr(chat_service, "_execute_sql", fake_execute_sql)
    monkeypatch.setattr(chat_service, "_gemini_api_keys", lambda: ["fake-key"])
    monkeypatch.setattr(chat_service, "_get_gemini_model", lambda _api_key: object())
    monkeypatch.setattr(chat_service, "MAIN_PROMPT", FakePromptTemplate("main"))
    monkeypatch.setattr(chat_service.ChatPromptTemplate, "from_messages", lambda *_args, **_kwargs: FakePromptTemplate("response"))

    response = asyncio.run(chat_service.chat_with_gemini("user-1", "Qual o valor?"))

    assert response == "Resposta final"
