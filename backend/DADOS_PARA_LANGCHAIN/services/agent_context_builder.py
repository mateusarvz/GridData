"""
build_agent_schema_context — produces a DDL-like text description of the user's schema
for injection into a LangChain SQL Agent prompt.

IMPORTANT — schema-only, NO row data:
This function returns ONLY table names, column names, types, nullability, and FK
relationships. It NEVER includes actual row data. Real data is accessed ONLY when
the SQL Agent executes a generated query against a read-only, user-restricted
database connection at runtime.

Security:
- user_id must come from the authenticated session, never from client input.
- Table names in the output are validated against the users_table whitelist.
- The output contains no user_id values or any data rows.

Implementation note:
  SchemaRepository uses the Supabase service client (REST/RPC) internally.
  No SQLAlchemy session is required.
"""

from DADOS_PARA_LANGCHAIN.services.schema_repository import SchemaRepository


async def build_agent_schema_context(user_id: str) -> str:
    """
    Build a plain-text DDL-like description of the user's database schema.

    This string is designed to be injected directly into the SQL Agent's system prompt
    so it understands which tables exist, their columns, and how they relate to
    users_table. The agent uses this context to generate valid SQL queries.

    Args:
        user_id: Authenticated user ID (from JWT/session, never from client input).
        session: SQLAlchemy AsyncSession connected to the system database.

    Returns:
        A multi-line string describing every table, its columns, and its FK
        relationship to users_table, formatted as simplified DDL.

    Example output:
        -- Tabela: departamentos (origem: departamentos.csv, 120 linhas)
        CREATE TABLE table_schema.departamentos (
            departamento_id bigint NOT NULL,
            nome_departamento text NOT NULL,
            andar bigint NOT NULL,
            users_table_id uuid NOT NULL REFERENCES table_schema.users_table(id)
        );

        -- Tabela: funcionarios (origem: RH_2024.xlsx, 4500 linhas)
        CREATE TABLE table_schema.funcionarios (
            funcionario_id bigint NOT NULL,
            nome text NOT NULL,
            salario numeric(10,2),
            users_table_id uuid NOT NULL REFERENCES table_schema.users_table(id)
        );

    ⚠️ The agent may use these names in dynamic SQL queries, but ALL queries are
    executed against a read-only role and are scoped via users_table_id to prevent
    cross-user data leakage.
    """
    repo = SchemaRepository()
    tables = await repo.build_full_schema(user_id)

    if not tables:
        return "-- Nenhuma tabela cadastrada para este usuário."

    lines: list[str] = [
        "-- ==============================================================",
        "-- ESQUEMA DE TABELAS DO USUÁRIO (SOMENTE ESTRUTURA)",
        "-- Nenhum dado de linha está incluído aqui.",
        "-- As tabelas residem no schema 'table_schema'.",
        "-- Cada tabela possui uma FK users_table_id -> table_schema.users_table.id",
        "-- que garante o isolamento entre usuários.",
        "-- ==============================================================",
        "",
    ]

    for t in tables:
        source_info = ""
        if t.origem_arquivo:
            source_info = f" (origem: {t.origem_arquivo}, {t.total_linhas} linhas)"
        lines.append(f"-- Tabela: {t.nome_tabela}{source_info}")
        lines.append(f"CREATE TABLE table_schema.{t.nome_tabela} (")

        col_defs: list[str] = []
        for col in t.colunas:
            nullable_str = "" if col.nullable else " NOT NULL"
            col_defs.append(f"    {col.nome} {col.tipo}{nullable_str}")

        # Append the FK relationship as a column definition
        if t.relacionamento:
            ref_parts = t.relacionamento.referencia.split(".")
            if len(ref_parts) == 3:
                col_defs.append(
                    f"    {t.relacionamento.coluna_local} uuid NOT NULL REFERENCES {ref_parts[0]}.{ref_parts[1]}({ref_parts[2]})"
                )

        lines.append(",\n".join(col_defs))
        lines.append(");")
        lines.append("")

    return "\n".join(lines)
