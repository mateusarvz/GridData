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
        "e pode executar consultas SQL SELECT para buscar dados.\n\n"
        "REGRAS:\n"
        "1. Se a pergunta pode ser respondida APENAS com a estrutura das tabelas (nomes, colunas, "
        "tipos, relacionamentos), responda diretamente sem gerar SQL.\n"
        "2. Se precisar de dados das linhas, gere uma query SQL SELECT válida.\n"
        "3. A query deve usar SOMENTE o schema 'table_schema'.\n"
        "4. A query deve ser APENAS SELECT (read-only).\n"
        "5. Responda EM PORTUGUÊS.\n\n"
        "Formato da resposta:\n"
        "- Se for responder sem SQL: apenas a resposta, sem formatação especial.\n"
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


async def _execute_sql(sql_query: str) -> list[dict]:
    """Execute a SQL query via the Supabase execute_sql_readonly RPC."""
    client = get_supabase_service_client()
    if client is None:
        raise RuntimeError("Supabase service client não configurado.")

    def _run():
        return client.rpc("execute_sql_readonly", {"sql_query": sql_query}).execute()

    import asyncio
    from functools import partial
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, partial(_run))
    rows = getattr(response, "data", None) or []
    return rows


async def chat_with_gemini(user_id: str, pergunta: str) -> str:
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
    })
    resposta_raw = _extract_text(result.content).strip()

    # Step 3: Check if Gemini generated SQL (separator '---DADOS---')
    if "---DADOS---" in resposta_raw:
        partes = resposta_raw.split("---DADOS---", 1)
        sql_query = partes[0].strip()

        # Clean SQL
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        # Execute SQL
        try:
            resultados = await _execute_sql(sql_query)
        except Exception as exc:
            resultados = [{"erro": str(exc)}]

        # Step 4: Generate final response with the data
        response_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Com base nos resultados da consulta SQL e na pergunta original, "
                "gere uma resposta clara e objetiva em português.\n\n"
                "Pergunta: {pergunta}\n"
                "Resultados: {resultados}"
            ),
            ("human", "Responda em português de forma clara e objetiva."),
        ])

        final = await (response_prompt | llm).ainvoke({
            "pergunta": pergunta,
            "resultados": str(resultados),
        })
        return _extract_text(final.content).strip()

    # No SQL needed — return the direct answer
    return resposta_raw