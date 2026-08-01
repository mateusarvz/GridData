import base64
import json
from io import BytesIO
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.core.supabase import get_supabase_service_client
from DADOS_PARA_LANGCHAIN.services.agent_context_builder import (
    build_agent_schema_context,
)

matplotlib.use("Agg")

QUERY_PLAN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "\n".join([
            "Você é um gerador de consultas SQL para dashboards gráficos.",
            "Receba o schema do usuário e o prompt em linguagem natural.",
            "Crie consultas SELECT projetadas para gerar",
            "dataframes diferentes.",
            "Cada dataframe deve ser usado por um gráfico.",
            "Priorize o tipo de gráfico pedido pelo usuário.",
            "Use apenas nomes exatos de tabelas e colunas do schema.",
            "Não invente tabelas ou colunas que não existam.",
            "Retorne apenas JSON válido no formato especificado.",
            "Sem texto extra.",
            "",
            "Formato esperado:",
            "{{",
            "  \"dashboards\": [",
            "    {{",
            "      \"id\": \"df1\",",
            "      \"sql\": \"SELECT ...\",",
            "      \"chart_type\": \"bar|column|line|pie|scatter\",",
            "      \"reason\": \"Motivo da query e do gráfico\",",
            "      \"description\": \"Breve descrição do que o gráfico\"",
            "        mostra\"",
            "    }}",
            "  ]",
            "}}",
        ])
    ),
    (
        "human",
        "Schema do usuário:\n{contexto}\n\nPrompt do usuário:\n{pergunta}"
    ),
])

RECIPE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "\n".join([
            "Você é um gerador de receita de gráfico.",
            "Recebe o prompt do usuário, as consultas SQL geradas.",
            "Inclua a documentação de cada query.",
            "Inclua também uma pré-visualização dos dataframes gerados.",
            "Produza apenas JSON válido. Use o mesmo id de cada item.",
            "Cada item deve descrever como desenhar o gráfico com Matplotlib.",
            "Inclua title, chart_type, x, y, description e notes.",
            "Para pizza, use label e value.",
            "Para linha ou coluna, use x e y.",
            "",
            "Formato esperado:",
            "{{",
            "  \"recipes\": [",
            "    {{",
            "      \"id\": \"df1\",",
            "      \"chart_type\": \"bar|column|line|pie|scatter\",",
            "      \"title\": \"Título do gráfico\",",
            "      \"description\": \"O que o gráfico mostra\",",
            "      \"x\": \"nome_coluna_x\",",
            "      \"y\": [\"nome_coluna_y\"],",
            "      \"notes\": \"Por que esse gráfico é útil\"",
            "    }}",
            "  ]",
            "}}",
        ])
    ),
    (
        "human",
        "\n".join([
            "Prompt do usuário: {pergunta}",
            "",
            "Consultas geradas e documentação:\n{queries_json}",
            "",
            "Pré-visualização dos dataframes:\n{preview_json}",
        ])
    ),
])


def _extract_text(content: Any) -> str:
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def _extract_json(text: str) -> str:
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
    elif cleaned.startswith("```") and "```" in cleaned[3:]:
        cleaned = cleaned[3:].rsplit("```", 1)[0]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start:end + 1]
    return cleaned


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
        " insert ",
        " update ",
        " delete ",
        " drop ",
        " alter ",
        " create ",
        " truncate ",
        " grant ",
        " revoke ",
        " merge ",
        " copy ",
        " call ",
        " do ",
        " execute ",
        " prepare ",
        " deallocate ",
        " vacuum ",
        " analyze ",
        " reindex ",
        " refresh ",
        " cluster ",
        " discard ",
        " set role ",
    )
    padded = f" {lowered} "
    return not any(token in padded for token in banned)


async def _execute_sql(sql_query: str) -> list[dict]:
    client = get_supabase_service_client()
    if client is None:
        raise RuntimeError("Supabase service client não configurado.")

    sql_query = _normalize_sql_query(sql_query)
    if not _is_safe_select_sql(sql_query):
        raise RuntimeError("SQL inválido ou inseguro gerado pelo agente.")

    def _run():
        return client.rpc(
            "execute_sql_readonly",
            {"sql_query": sql_query},
        ).execute()

    import asyncio
    from functools import partial

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, partial(_run))
    rows = getattr(response, "data", None) or []
    if not isinstance(rows, list):
        raise RuntimeError("Resposta SQL inesperada do Supabase.")
    return rows


def _build_preview(rows: list[dict]) -> dict:
    if not rows:
        return {"columns": [], "rows": 0, "example": []}
    columns = list(rows[0].keys())
    example = rows[:5]
    return {"columns": columns, "rows": len(rows), "example": example}


def desenhista(
    recipe: dict,
    dataframes: dict[str, pd.DataFrame],
) -> list[dict]:
    charts: list[dict] = []

    for item in recipe.get("recipes", []):
        chart_id = item.get("id") or ""
        df = dataframes.get(chart_id)
        if df is None:
            charts.append({
                "id": chart_id,
                "title": item.get("title", "Gráfico não disponível"),
                "explanation": "DataFrame não encontrado para este gráfico.",
                "chart_type": item.get("chart_type", "bar"),
                "sql": item.get("sql", ""),
                "image_base64": "",
            })
            continue

        if df.empty:
            charts.append({
                "id": chart_id,
                "title": item.get("title", "Gráfico vazio"),
                "explanation": item.get(
                    "description",
                    "Nenhum dado retornado pela consulta.",
                ),
                "chart_type": item.get("chart_type", "bar"),
                "sql": item.get("sql", ""),
                "image_base64": "",
            })
            continue

        chart_type = (item.get("chart_type") or "bar").lower()
        x_column = item.get("x")
        y_value = item.get("y")
        if isinstance(y_value, str):
            y_columns = [y_value]
        elif isinstance(y_value, list):
            y_columns = y_value
        else:
            y_columns = []

        if not x_column and y_columns:
            x_column = df.columns[0]
        if not y_columns:
            y_columns = [
                c
                for c in df.columns
                if pd.api.types.is_numeric_dtype(df[c])
            ]
        if chart_type == "pie" and len(y_columns) > 1:
            y_columns = [y_columns[0]]

        fig, ax = plt.subplots(figsize=(8, 4))
        try:
            if chart_type in {"bar", "column"}:
                if not x_column or not y_columns:
                    raise ValueError(
                        "Colunas x ou y não definidas para gráfico de barras."
                    )
                for y_col in y_columns:
                    ax.bar(df[x_column].astype(str), df[y_col], label=y_col)
                ax.set_xlabel(x_column)
                ax.set_ylabel(", ".join(y_columns))
                ax.legend(fontsize=8)
            elif chart_type == "line":
                if not x_column or not y_columns:
                    raise ValueError(
                        "Colunas x ou y não definidas para gráfico de linha."
                    )
                for y_col in y_columns:
                    ax.plot(
                        df[x_column].astype(str),
                        df[y_col],
                        marker="o",
                        label=y_col,
                    )
                ax.set_xlabel(x_column)
                ax.set_ylabel(", ".join(y_columns))
                ax.legend(fontsize=8)
            elif chart_type == "pie":
                if not x_column or not y_columns:
                    raise ValueError(
                        "Coluna x ou y não definidas para gráfico de pizza."
                    )
                labels = df[x_column].astype(str).tolist()
                values = df[y_columns[0]].tolist()
                ax.pie(
                    values,
                    labels=labels,
                    autopct="%1.1f%%",
                    textprops={"fontsize": 8},
                )
            elif chart_type == "scatter":
                if len(y_columns) < 1 or not x_column:
                    raise ValueError(
                        "Colunas x ou y não definidas para gráfico de"
                        " dispersão."
                    )
                ax.scatter(df[x_column].astype(str), df[y_columns[0]])
                ax.set_xlabel(x_column)
                ax.set_ylabel(y_columns[0])
            else:
                if not x_column or not y_columns:
                    raise ValueError(
                        "Colunas x ou y não definidas para gráfico."
                    )
                for y_col in y_columns:
                    ax.bar(df[x_column].astype(str), df[y_col], label=y_col)
                ax.set_xlabel(x_column)
                ax.set_ylabel(", ".join(y_columns))
                ax.legend(fontsize=8)

            ax.set_title(item.get("title", ""))
            ax.tick_params(axis="x", rotation=30)
            plt.tight_layout()
            buffer = BytesIO()
            fig.savefig(buffer, format="png", dpi=120)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        except Exception as exc:
            plt.close(fig)
            charts.append({
                "id": chart_id,
                "title": item.get("title", "Gráfico falhou"),
                "explanation": f"Falha ao desenhar gráfico: {exc}",
                "chart_type": chart_type,
                "sql": item.get("sql", ""),
                "image_base64": "",
            })
            continue
        finally:
            plt.close(fig)

        charts.append({
            "id": chart_id,
            "title": item.get("title", "Gráfico"),
            "explanation": item.get("description", item.get("notes", "")),
            "chart_type": chart_type,
            "sql": item.get("sql", ""),
            "image_base64": image_base64,
        })

    return charts


def _get_gemini_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.1,
    )


async def build_dashboard(
    user_id: str,
    pergunta: str,
    nome_usuario: str | None = None,
) -> dict:
    contexto = await build_agent_schema_context(user_id)
    if not contexto.strip() or "CREATE TABLE" not in contexto:
        raise RuntimeError(
            "Nenhuma tabela encontrada para o seu usuário. "
            "Faça upload de dados primeiro."
        )

    llm = _get_gemini_model()

    step1 = await (QUERY_PLAN_PROMPT | llm).ainvoke({
        "contexto": contexto,
        "pergunta": pergunta,
    })
    query_text = _extract_text(step1.content)
    query_json = _extract_json(query_text)
    plan = json.loads(query_json)
    if not isinstance(plan, dict) or "dashboards" not in plan:
        raise RuntimeError(
            "Resposta do Gemini não continha a estrutura de dashboards "
            "esperada."
        )

    dataframes: dict[str, pd.DataFrame] = {}
    preview_items = []
    for item in plan.get("dashboards", []):
        sql = _normalize_sql_query(item.get("sql", ""))
        item_id = item.get("id") or f"df{len(dataframes)+1}"
        item["id"] = item_id
        if not sql:
            raise RuntimeError(f"Query ausente para item {item_id}.")

        rows = await _execute_sql(sql)
        df = pd.DataFrame(rows)
        dataframes[item_id] = df
        preview_items.append({
            "id": item_id,
            "sql": sql,
            "reason": item.get("reason", ""),
            "description": item.get("description", ""),
            "preview": _build_preview(rows),
        })

    preview_map = {
        item["id"]: item["preview"]
        for item in preview_items
    }
    recipe_input = {
        "pergunta": pergunta,
        "queries_json": json.dumps(
            preview_items,
            ensure_ascii=False,
            indent=2,
        ),
        "preview_json": json.dumps(
            preview_map,
            ensure_ascii=False,
            indent=2,
        ),
    }
    step2 = await (RECIPE_PROMPT | llm).ainvoke(recipe_input)
    recipe_text = _extract_text(step2.content)
    recipe_json = _extract_json(recipe_text)
    recipe = json.loads(recipe_json)
    if not isinstance(recipe, dict) or "recipes" not in recipe:
        raise RuntimeError(
            "Resposta do Gemini não continha a estrutura de receita "
            "esperada."
        )

    raw_queries = plan.get("dashboards", [])
    charts = desenhista({**recipe, **{"raw_queries": raw_queries}}, dataframes)
    return {
        "charts": charts,
        "raw_plan": plan,
        "raw_recipe": recipe,
    }
