"""
Build plain-text schema context for LangChain SQL Agent.

Goal: expose real schema only, with exact table/column names, before any query
is generated. No row data included here.
"""

import json

from DADOS_PARA_LANGCHAIN.services.schema_repository import SchemaRepository


async def build_agent_schema_context(user_id: str) -> str:
    repo = SchemaRepository()
    tables = await repo.build_full_schema(user_id)

    if not tables:
        return "-- Nenhuma tabela cadastrada para este usuário."

    lines: list[str] = [
        "-- ==============================================================",
        "-- ESQUEMA REAL DO USUÁRIO",
        "-- USE SOMENTE NOMES EXATOS DE TABELAS E COLUNAS.",
        "-- NÃO invente colunas como 'Date' se o schema real não tiver esse nome.",
        "-- Tabelas residem em table_schema.",
        "-- Cada tabela tem users_table_id -> table_schema.users_table.id.",
        "-- ==============================================================",
        "",
    ]

    schema_payload: list[dict] = []

    for t in tables:
        source_info = ""
        if t.origem_arquivo:
            source_info = f" (origem: {t.origem_arquivo}, {t.total_linhas} linhas)"
        lines.append(f"-- Tabela: {t.nome_tabela}{source_info}")
        lines.append(f"CREATE TABLE table_schema.{t.nome_tabela} (")

        col_defs: list[str] = []
        json_cols: list[dict] = []
        for col in t.colunas:
            nullable_str = "" if col.nullable else " NOT NULL"
            col_defs.append(f"    {col.nome} {col.tipo}{nullable_str}")
            json_cols.append(
                {
                    "nome": col.nome,
                    "tipo": col.tipo,
                    "nullable": col.nullable,
                }
            )

        if t.relacionamento:
            ref_parts = t.relacionamento.referencia.split(".")
            if len(ref_parts) == 3:
                col_defs.append(
                    f"    {t.relacionamento.coluna_local} uuid NOT NULL REFERENCES {ref_parts[0]}.{ref_parts[1]}({ref_parts[2]})"
                )

        lines.append(",\n".join(col_defs))
        lines.append(");")
        lines.append("")
        schema_payload.append(
            {
                "nome_tabela": t.nome_tabela,
                "colunas": json_cols,
                "relacionamento": None if not t.relacionamento else {
                    "coluna_local": t.relacionamento.coluna_local,
                    "referencia": t.relacionamento.referencia,
                },
            }
        )

    lines.extend([
        "-- ==============================================================",
        "-- SCHEMA ESTRUTURADO EM JSON",
        "-- FONTE DE VERDADE PARA NOMES EXATOS.",
        json.dumps(schema_payload, ensure_ascii=False, indent=2),
    ])

    return "\n".join(lines)
