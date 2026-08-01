"""
ChatService — LangChain + Gemini chat for querying Supabase via SQL.

Flow:
1. User sends a question in natural language
2. Schema context (DDL) for the user is fetched from the existing repository
3. Gemini decides: answer from schema context OR generate a SELECT query
4. If SQL needed, executes via Supabase execute_sql_readonly RPC
5. Gemini generates a natural language response
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import re
from app.core.config import settings
from app.core.supabase import get_supabase_service_client
from DADOS_PARA_LANGCHAIN.services.agent_context_builder import (
    build_agent_schema_context,
)

# ── Prompt: decide if SQL is needed, then answer ──

MAIN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Você é um assistente de análise de dados. Você tem acesso ao schema das tabelas do usuário "
        "e pode executar consultas SQL SELECT para buscar dados.\n"
        "Nome do usuário: {nome_usuario}\n\n"
        "REGRAS:\n"
        "0. Antes de montar qualquer SQL, leia o schema real abaixo.\n"
        "1. Se a pergunta pode ser respondida consultar dados sobre as tabelas, responda diretamente sem gerar SQL.\n"
        "2. Se precisar de dados das linhas, gere uma query SQL de consulta válido.\n"
        "3. A query deve usar SOMENTE o schema 'table_schema'.\n"
        "4. Se nao encontrar alguma linha ou coluna ou tabela, diga que nao encontrou os dados necessários.\n"
        "5. Sempre use aspas duplas em identificadores quando houver risco de capitalização específica.\n"
        "6. Responda EM PORTUGUÊS.\n\n"
        "7. Só use o nome do usuário quando soar natural e útil.\n"
        "8. Por padrão, responda curto, direto e objetivo. Só detalhe muito quando o usuário pedir explicitamente 'explique melhor', 'detalhe isso', 'por que' ou equivalente.\n"
        "9. Formate SEMPRE em Markdown limpo quando houver conteúdo com múltiplos itens, destaque, listas ou títulos. Use listas para rankings, etapas e conjuntos de dados.\n"
        "10. Use **negrito** para valores importantes, nomes relevantes e valores monetários.\n\n"
        "11. O prompt do humano deve ter prioridade sobre outras regras quando gerar uma resposta"
        "Formato da resposta:\n"
        "- Se for responder sem SQL: responda em Markdown limpo, com brevidade por padrão.\n"
        "- Se for necessário SQL: primeiro a query SQL pura (sem markdown, sem explicações), "
        "depois uma linha com '---DADOS---' e então a resposta final.\n\n"
        "Schema do banco de dados:\n{contexto}"
    ),
    ("human", "{pergunta}"),
])


def _get_gemini_model() -> ChatGoogleGenerativeAI:
    """Initialize the Gemini model from settings."""
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.1,
    )


def _extract_text(content) -> str:
    """Extract text from content that may be a list (multimodal) or a plain string."""
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return content


def _normalize_sql_query(sql_query: str) -> str:
    sql = (sql_query or "").strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    sql = sql.rstrip(";").strip()
    return sql


def _is_safe_select_sql(sql_query: str) -> bool:
    sql = _normalize_sql_query(sql_query)
    if not sql:
        return False

    lowered = sql.lower()
    if not lowered.startswith("select") and not lowered.startswith("with"):
        return False

    if ";" in sql:
        return False

    banned = (
        " insert ", " update ", " delete ", " drop ", " alter ", " create ",
        " truncate ", " grant ", " revoke ", " merge ", " copy ", " call ",
        " do ", " execute ", " prepare ", " deallocate ", " vacuum ", " analyze ",
        " reindex ", " refresh ", " cluster ", " discard ", " set role ",
    )
    padded = f" {lowered} "
    if any(token in padded for token in banned):
        return False

    return True


async def _execute_sql(sql_query: str) -> list[dict]:
    """Execute a SQL query via the Supabase execute_sql_readonly RPC."""
    client = get_supabase_service_client()
    if client is None:
        raise RuntimeError("Supabase service client não configurado.")

    sql_query = _normalize_sql_query(sql_query)
    if not _is_safe_select_sql(sql_query):
        raise RuntimeError("SQL inválido ou inseguro gerado pelo agente.")

    def _run():
        return client.rpc("execute_sql_readonly", {"sql_query": sql_query}).execute()

    import asyncio
    from functools import partial
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, partial(_run))
    rows = getattr(response, "data", None) or []
    return rows


async def chat_with_gemini(user_id: str, pergunta: str, nome_usuario: str | None = None) -> str:
    """
    Process a user question using LangChain + Gemini.

    Steps:
    1. Fetch schema context for the user
    2. Ask Gemini to answer (with optional SQL generation)
    3. If SQL was generated, execute it and get final answer
    4. Return the response
    """
    # Step 1: Get schema context
    contexto = await build_agent_schema_context(user_id)
    if not contexto.strip() or "CREATE TABLE" not in contexto:
        return (
            "Nenhuma tabela encontrada para o seu usuário. "
            "Faça upload de dados primeiro para poder usar o chat."
        )

    llm = _get_gemini_model()
    chain = MAIN_PROMPT | llm

    # Step 2: Ask Gemini — may return just text or text + SQL
    result = await chain.ainvoke({
        "contexto": contexto,
        "pergunta": pergunta,
        "nome_usuario": nome_usuario or "Usuário",
    })
    resposta_raw = _extract_text(result.content).strip()

    # Step 3: Check if Gemini generated SQL (separator '---DADOS---')
    if "---DADOS---" in resposta_raw:
        partes = resposta_raw.split("---DADOS---", 1)
        sql_query = _normalize_sql_query(partes[0])

        # Execute SQL
        try:
            resultados = await _execute_sql(sql_query)
        except Exception as exc:
            resultados = [{"erro": str(exc)}]

        # Step 4: Generate final response with the data
        response_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Com base nos resultados da consulta SQL, na pergunta original, "
                "gere uma resposta clara, objetiva e em Markdown limpo em português.\n"
                "Seja curto e direto.\n"
                "Caso ache necessario usar Tabelas, use um Markdown bem estruturado, com linhas e colunas bem definidas"
                "Use listas, títulos curtos e **negrito** para dados importantes.\n\n"
                "Pergunta: {pergunta}\n"
                "Resultados: {resultados}"
            ),
            ("human", "Responda em português, em Markdown limpo, com tom natural."),
        ])

        final = await (response_prompt | llm).ainvoke({
            "pergunta": pergunta,
            "resultados": str(resultados),
            "nome_usuario": nome_usuario or "Usuário",
        })
        return _extract_text(final.content).strip()

    # No SQL needed — return the direct answer
    return resposta_raw
