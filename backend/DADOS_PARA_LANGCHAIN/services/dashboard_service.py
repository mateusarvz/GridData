import base64
import json
from io import BytesIO
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from matplotlib.ticker import FuncFormatter
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings
from app.core.supabase import get_supabase_service_client
from DADOS_PARA_LANGCHAIN.services.agent_context_builder import (
    build_agent_schema_context,
)

matplotlib.use("Agg")
FIG_BG_COLOR = "#020617"
AXIS_BG_COLOR = "#0f172a"
GRID_COLOR = "#334155"
TEXT_COLOR = "#E2E8F0"
TEXT_SECONDARY = "#94A3B8"
SPINE_COLOR = "#475569"
PALETTE = [
    "#5C2392",
    "#6E43B9",
    "#4E2B96",
    "#725DC7",
    "#67379C",
    "#2E2835",
]
DEFAULT_BAR_COLOR = PALETTE[1]

QUERY_PLAN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "\n".join([
            "Você é um gerador de plano de dashboard com IA.",
            "Receba o schema do usuário e o prompt em linguagem natural.",
            "Caso o usuario nao diga o nome exato das tabelas e das colunas, voce deve analisar o schema e adivinhar de qual tabela e de qual coluna o usuario está falando",
            "Ao tentar adivinhar o nome das tabelas e colunas, suas opções devem ser somente nomes de tabela e coluna exatamente como aparecem no esquema recebido.",
            "Sempre escreva com aspas duplas SQL exatas.",
            "Organize os blocos em ordem lógica para o usuário entender a análise rapidamente.",
            "Gere uma análise detalhada com vários blocos de gráficos, tabelas e cards KPI, incluindo múltiplos insights, correlações e recomendações.",
            "Gere entre 10 e 20 itens no total, deixando o próprio Gemini decidir quantos blocos são relevantes com base no prompt do usuário, no schema do banco de dados e nas informações disponíveis.",
            "Os labels de eixo x e y devem ser específicos, intuitivos e representativos da query usada para obter os dados, especialmente em análises detalhadas.",
            "Para cada card e cada bloco de texto, gere sempre os campos description e content. A description deve ser detalhada e explicativa, e o content deve expandir o insight com contexto e implicações.",
            "Sempre inclua campos x_label e y_label descritivos em charts para que os eixos fiquem claros e ligados à lógica da query.",
            "Inclua ao menos um bloco de texto analítico (item_type: text) que explique em largura total o que a análise do Gemini encontrou e como os gráficos, tabelas e cards são relevantes para o prompt do usuário.",
            "Priorize gerar pelo menos 2 gráficos, 1 tabela, 2 cards KPI e 1 bloco de texto sempre que houver dados suficientes.",
            "Retorne apenas JSON válido no formato especificado.",
            "Sem texto extra.",
            "",
            "Formato esperado:",
            "{{",
            "  \"elements\": [",
            "    {{",
            "      \"id\": \"item1\",",
            "      \"item_type\": \"chart|table|card|text\",",
            "      \"title\": \"Título do bloco\",",
            "      \"description\": \"Breve descrição do bloco\",",
            "      \"sql\": \"SELECT ...\",",
            "      \"chart_type\": \"bar|column|line|pie|scatter\",",
            "      \"content\": \"Texto explicativo ou resumo\",",
            "      \"reason\": \"Por que este bloco foi escolhido\"",
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
            "Você é um gerador de receita de dashboard para renderização.",
            "Recebe o prompt do usuário, os blocos gerados e pré-visualização de dados.",
            "Produza uma receita que maximize a profundidade analítica e a relevância do dashboard para o prompt.",
            "Para cada card, gere explicitamente os campos description e content. description deve ser curto e objetivo; content deve explicar o insight ou a métrica do card.",
            "Inclua um bloco de texto em largura total que resuma o insight principal, descrevendo o que o Gemini encontrou e por que os elementos são relevantes.",
            "Evite usar números como categorias. Dê prioridade a colunas de texto.",
            "Inclua documentação de cada bloco.",
            "Produza apenas JSON válido. Use o mesmo id de cada item.",
            "Formato esperado:",
            "{{",
            "  \"recipes\": [",
            "    {{",
            "      \"id\": \"item1\",",
            "      \"item_type\": \"chart|table|card|text\",",
            "      \"title\": \"Título do bloco\",",
            "      \"description\": \"Explicação do bloco\",",
            "      \"chart_type\": \"bar|column|line|pie|scatter\",",
            "      \"x\": \"nome_coluna_x\",",
            "      \"y\": [\"nome_coluna_y\"],",
            "      \"x_label\": \"Label descritivo para o eixo X\",",
            "      \"y_label\": \"Label descritivo para o eixo Y\",",
            "      \"content\": \"Texto para card ou bloco de análise\",",
            "      \"notes\": \"Por que esse bloco é útil\"",
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
            "Blocos gerados:\n{queries_json}",
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


def _prepare_axis_labels(values: pd.Series) -> tuple[list[int], list[str]]:
    labels = []
    for value in values:
        if pd.isna(value):
            labels.append("")
        else:
            labels.append(str(value))
    return list(range(len(labels))), labels


def _format_tick_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        text = format(float(value), ".15g")
        return text if text != "-0" else "0"
    return str(value)


def _get_palette(n: int) -> list[str]:
    if n <= len(PALETTE):
        return PALETTE[:n]
    return [PALETTE[i % len(PALETTE)] for i in range(n)]


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


def _prepare_table_data(df: pd.DataFrame, limit: int = 20) -> dict:
    columns = [str(col) for col in df.columns.tolist()]
    rows = [
        [None if pd.isna(val) else val for val in row]
        for row in df.head(limit).to_numpy().tolist()
    ]
    return {
        "columns": columns,
        "rows": rows,
        "rows_count": len(df),
    }


def desenhista(
    recipe: dict,
    dataframes: dict[str, pd.DataFrame],
) -> list[dict]:
    charts: list[dict] = []

    for item in recipe.get("recipes", []):
        item_id = item.get("id") or ""
        item_type = (item.get("item_type") or "chart").lower()
        df = dataframes.get(item_id)

        if item_type == "table":
            if df is None:
                charts.append({
                    "id": item_id,
                    "item_type": item_type,
                    "title": item.get("title", "Tabela não disponível"),
                    "description": item.get("description", "Tabela sem dados."),
                    "sql": item.get("sql", ""),
                    "content": item.get("content", ""),
                    "table_data": None,
                    "reason": item.get("reason", ""),
                })
                continue

            charts.append({
                "id": item_id,
                "item_type": item_type,
                "title": item.get("title", "Tabela"),
                "description": item.get("description", item.get("notes", "")),
                "sql": item.get("sql", ""),
                "content": item.get("content", ""),
                "table_data": _prepare_table_data(df),
                "reason": item.get("reason", ""),
            })
            continue

        if item_type in {"card", "text"}:
            const_description = item.get("description") or item.get("notes") or item.get("content") or ""
            const_content = item.get("content") or item.get("description") or item.get("notes") or ""
            charts.append({
                "id": item_id,
                "item_type": item_type,
                "title": item.get("title", ""),
                "description": const_description,
                "sql": item.get("sql", ""),
                "content": const_content,
                "reason": item.get("reason", ""),
                "image_base64": "",
                "chart_type": item.get("chart_type", ""),
            })
            continue

        if df is None:
            charts.append({
                "id": item_id,
                "item_type": item_type,
                "title": item.get("title", "Gráfico não disponível"),
                "description": "DataFrame não encontrado para este gráfico.",
                "chart_type": item.get("chart_type", "bar"),
                "sql": item.get("sql", ""),
                "image_base64": "",
                "reason": item.get("reason", ""),
            })
            continue

        if df.empty:
            charts.append({
                "id": item_id,
                "item_type": item_type,
                "title": item.get("title", "Gráfico vazio"),
                "description": item.get(
                    "description",
                    "Nenhum dado retornado pela consulta.",
                ),
                "chart_type": item.get("chart_type", "bar"),
                "sql": item.get("sql", ""),
                "image_base64": "",
                "reason": item.get("reason", ""),
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

        x_label = item.get("x_label") or x_column or "Eixo X"
        y_label = item.get("y_label") or (
            ", ".join(y_columns) if y_columns else "Eixo Y"
        )

        fig, ax = plt.subplots(figsize=(10, 5), facecolor=FIG_BG_COLOR)
        ax.set_facecolor(AXIS_BG_COLOR)
        fig.patch.set_facecolor(FIG_BG_COLOR)
        try:
            if not x_column or not y_columns:
                raise ValueError("Colunas x ou y não definidas para gráfico.")

            x_positions, x_labels = _prepare_axis_labels(df[x_column])
            palette = _get_palette(len(y_columns))

            ax.set_axisbelow(True)
            ax.grid(color=GRID_COLOR, linestyle="--", linewidth=0.8, alpha=0.4)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(SPINE_COLOR)
            ax.spines["bottom"].set_color(SPINE_COLOR)
            ax.tick_params(colors=TEXT_SECONDARY, which="both")
            ax.xaxis.label.set_color(TEXT_COLOR)
            ax.yaxis.label.set_color(TEXT_COLOR)
            ax.title.set_color(TEXT_COLOR)

            if chart_type in {"bar", "column"}:
                for idx, y_col in enumerate(y_columns):
                    y_values = pd.to_numeric(df[y_col], errors="coerce").fillna(0)
                    ax.bar(
                        x_positions,
                        y_values,
                        label=y_col,
                        color=palette[idx],
                        edgecolor=FIG_BG_COLOR,
                        linewidth=0.8,
                    )
                ax.set_xlabel(x_column)
                ax.set_ylabel(", ".join(y_columns))
                ax.set_xticks(x_positions)
                ax.set_xticklabels(x_labels, rotation=30, ha="right", color=TEXT_SECONDARY)
                ax.legend(
                    fontsize=8,
                    frameon=True,
                    facecolor=AXIS_BG_COLOR,
                    edgecolor=SPINE_COLOR,
                    framealpha=0.85,
                    labelcolor=TEXT_COLOR,
                )
            elif chart_type == "line":
                for idx, y_col in enumerate(y_columns):
                    y_values = pd.to_numeric(df[y_col], errors="coerce").fillna(0)
                    ax.plot(
                        x_positions,
                        y_values,
                        marker="o",
                        markerfacecolor="white",
                        markeredgewidth=1.8,
                        markeredgecolor=palette[idx],
                        color=palette[idx],
                        linewidth=2.2,
                        label=y_col,
                    )
                ax.set_xlabel(x_column)
                ax.set_ylabel(", ".join(y_columns))
                ax.set_xticks(x_positions)
                ax.set_xticklabels(x_labels, rotation=30, ha="right", color=TEXT_SECONDARY)
                ax.legend(
                    fontsize=8,
                    frameon=True,
                    facecolor=AXIS_BG_COLOR,
                    edgecolor=SPINE_COLOR,
                    framealpha=0.85,
                    labelcolor=TEXT_COLOR,
                )
            elif chart_type == "pie":
                labels = x_labels
                values = pd.to_numeric(df[y_columns[0]], errors="coerce").fillna(0).tolist()
                wedges, texts, autotexts = ax.pie(
                    values,
                    labels=labels,
                    autopct="%1.1f%%",
                    textprops={"fontsize": 9, "color": TEXT_COLOR},
                    colors=_get_palette(len(values)),
                    wedgeprops={"edgecolor": FIG_BG_COLOR, "linewidth": 1.2},
                    pctdistance=0.78,
                )
                for text in texts + autotexts:
                    text.set_color(TEXT_COLOR)
                ax.set_ylabel("")
            elif chart_type == "scatter":
                y_values = pd.to_numeric(df[y_columns[0]], errors="coerce").fillna(0)
                ax.scatter(
                    x_positions,
                    y_values,
                    color=palette[0],
                    edgecolors="white",
                    linewidth=0.9,
                    s=90,
                    alpha=0.92,
                )
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
                ax.set_xticks(x_positions)
                ax.set_xticklabels(x_labels, rotation=30, ha="right", color=TEXT_SECONDARY)
            else:
                for idx, y_col in enumerate(y_columns):
                    y_values = pd.to_numeric(df[y_col], errors="coerce").fillna(0)
                    ax.bar(
                        x_positions,
                        y_values,
                        label=y_col,
                        color=palette[idx],
                        edgecolor=FIG_BG_COLOR,
                        linewidth=0.8,
                    )
                ax.set_xlabel(x_column)
                ax.set_ylabel(", ".join(y_columns))
                ax.set_xticks(x_positions)
                ax.set_xticklabels(x_labels, rotation=30, ha="right", color=TEXT_SECONDARY)
                ax.legend(
                    fontsize=8,
                    frameon=True,
                    facecolor=AXIS_BG_COLOR,
                    edgecolor=SPINE_COLOR,
                    framealpha=0.85,
                    labelcolor=TEXT_COLOR,
                )

            ax.set_title(item.get("title", ""), fontsize=14, pad=14)
            ax.tick_params(axis="x", rotation=30)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: _format_tick_value(value)))
            plt.tight_layout(pad=0.5, h_pad=0.5, w_pad=0.5)
            buffer = BytesIO()
            fig.savefig(buffer, format="png", dpi=120, facecolor=FIG_BG_COLOR, bbox_inches="tight")
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        except Exception as exc:
            plt.close(fig)
            charts.append({
                "id": item_id,
                "item_type": item_type,
                "title": item.get("title", "Gráfico falhou"),
                "description": item.get("description", ""),
                "chart_type": chart_type,
                "sql": item.get("sql", ""),
                "image_base64": "",
                "content": item.get("content", ""),
                "reason": item.get("reason", ""),
            })
            continue
        finally:
            plt.close(fig)

        charts.append({
            "id": item_id,
            "item_type": item_type,
            "title": item.get("title", "Gráfico"),
            "description": item.get("description") or item.get("notes") or item.get("content") or item.get("reason") or "",
            "chart_type": chart_type,
            "sql": item.get("sql", ""),
            "image_base64": image_base64,
            "content": item.get("content", ""),
            "reason": item.get("reason", ""),
            "x_label": x_label,
            "y_label": y_label,
        })

    return charts


def _get_gemini_model(api_key: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=api_key,
        temperature=0.1,
    )


def _gemini_api_keys() -> list[str]:
    return getattr(settings, "GEMINI_API_KEYS", [])


async def _invoke_with_gemini_fallback(prompt_template, params):
    last_exc = None
    for api_key in _gemini_api_keys():
        llm = _get_gemini_model(api_key)
        chain = prompt_template | llm
        try:
            return await chain.ainvoke(params)
        except Exception as exc:
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Nenhuma chave Gemini configurada.")


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

    step1 = await _invoke_with_gemini_fallback(QUERY_PLAN_PROMPT, {
        "contexto": contexto,
        "pergunta": pergunta,
    })
    query_text = _extract_text(step1.content)
    query_json = _extract_json(query_text)
    plan = json.loads(query_json)
    if not isinstance(plan, dict) or ("dashboards" not in plan and "elements" not in plan):
        raise RuntimeError(
            "Resposta do Gemini não continha a estrutura de dashboards "
            "esperada."
        )

    elements = plan.get("elements", plan.get("dashboards", []))[:20]
    dataframes: dict[str, pd.DataFrame] = {}
    preview_items = []
    for item in elements:
        sql = _normalize_sql_query(item.get("sql", ""))
        item_id = item.get("id") or f"item{len(dataframes)+1}"
        item["id"] = item_id
        if not sql:
            continue

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
    step2 = await _invoke_with_gemini_fallback(RECIPE_PROMPT, recipe_input)
    recipe_text = _extract_text(step2.content)
    recipe_json = _extract_json(recipe_text)
    recipe = json.loads(recipe_json)
    if not isinstance(recipe, dict) or "recipes" not in recipe:
        raise RuntimeError(
            "Resposta do Gemini não continha a estrutura de receita "
            "esperada."
        )

    raw_elements = elements
    charts = desenhista({**recipe, **{"raw_queries": raw_elements}}, dataframes)
    return {
        "charts": charts,
        "raw_plan": plan,
        "raw_recipe": recipe,
    }
