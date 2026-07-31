"""
SchemaRepository — data-access layer for table_schema metadata.

Every query is filtered by user_id from the authenticated session (never from client input),
and table names used in dynamic queries come exclusively from the users_table whitelist.

Security guarantees (see project rules):
1. user_id is extracted from the JWT/session, never from request parameters.
2. Dynamic table names are validated against table_schema.users_table before use.
3. Information_schema queries are restricted to table_schema so no cross-schema leakage.
4. NO row data is ever fetched — only column names, types, and FK constraints.

Implementation note:
  We use the Supabase *service client* (REST/PostgREST) instead of a raw asyncpg
  SQLAlchemy session. Direct asyncpg connections to Supabase's port 5432 time out in
  this environment; the service client goes through the PostgREST HTTPS API, which
  is always available. Column metadata is retrieved via the `execute_sql_readonly`
  RPC function (SECURITY DEFINER, granted to service_role) so we can query
  information_schema without exposing a direct database socket.
"""

import asyncio
from functools import partial

from app.core.supabase import get_supabase_service_client
from DADOS_PARA_LANGCHAIN.models.estrutura_dto import (
    ColunaSchema,
    RelacionamentoInfo,
    TabelaSchema,
)

TABLE_SCHEMA = "table_schema"

# ---------------------------------------------------------------------------
# Helper — run synchronous supabase-py calls in a thread pool so they don't
# block the asyncio event loop.
# ---------------------------------------------------------------------------

async def _run_sync(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))


class SchemaRepository:
    """Repository for reading structural metadata about user-created tables.

    Uses the Supabase service client (REST API) to avoid direct database socket
    connections that time out in the current Supabase environment.
    """

    def __init__(self):
        self._client = get_supabase_service_client()

    # ------------------------------------------------------------------
    # Public API (mirrors the previous SQLAlchemy-based interface)
    # ------------------------------------------------------------------

    async def get_user_tables(self, user_id: str) -> list[dict]:
        """
        Fetch all entries in table_schema.users_table belonging to the authenticated user.

        This is the *whitelist* — every dynamic table query MUST validate against this list.
        Uses the Supabase service client so the call goes through PostgREST (HTTPS),
        not a direct database socket.
        """
        if self._client is None:
            return []

        def _fetch():
            return (
                self._client
                .schema(TABLE_SCHEMA)
                .from_("users_table")
                .select("id, nome_tabela, nome_origem_arquivo, tipo_arquivo, total_linhas, criado_em")
                .eq("user_id", user_id)
                .order("criado_em", desc=True)
                .execute()
            )

        response = await _run_sync(_fetch)
        rows = getattr(response, "data", None) or []
        return [
            {
                "id": str(r.get("id", "")),
                "nome_tabela": r.get("nome_tabela", ""),
                "nome_origem_arquivo": r.get("nome_origem_arquivo"),
                "tipo_arquivo": r.get("tipo_arquivo"),
                "total_linhas": r.get("total_linhas") or 0,
                "criado_em": r.get("criado_em"),
            }
            for r in rows
        ]

    async def get_table_columns(self, table_name: str) -> list[ColunaSchema]:
        """
        Retrieve column metadata from information_schema.columns for a single table.

        Uses the `execute_sql_readonly` RPC (SECURITY DEFINER, service_role) to query
        information_schema without a direct socket connection.

        SECURITY: table_name is expected to come from the users_table whitelist only.
        """
        if self._client is None:
            return []

        sql = (
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'table_schema' "
            f"  AND table_name = '{table_name}' "
            "ORDER BY ordinal_position"
        )

        def _fetch():
            return self._client.rpc("execute_sql_readonly", {"sql_query": sql}).execute()

        try:
            response = await _run_sync(_fetch)
            rows = getattr(response, "data", None) or []
            return [
                ColunaSchema(
                    nome=r["column_name"],
                    tipo=r["data_type"],
                    nullable=(r["is_nullable"] == "YES"),
                )
                for r in rows
            ]
        except Exception:
            return []

    async def get_table_relationship(self, table_name: str) -> RelacionamentoInfo | None:
        """
        Find the foreign-key constraint linking this table to table_schema.users_table.

        Uses the `execute_sql_readonly` RPC to query information_schema constraint views
        without a direct socket connection.
        """
        if self._client is None:
            return None

        sql = (
            "SELECT "
            "  kcu.column_name          AS coluna_local, "
            "  ccu.table_schema         AS schema_ref, "
            "  ccu.table_name           AS tabela_ref, "
            "  ccu.column_name          AS coluna_ref "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON tc.constraint_catalog = kcu.constraint_catalog "
            " AND tc.constraint_schema  = kcu.constraint_schema "
            " AND tc.constraint_name    = kcu.constraint_name "
            "JOIN information_schema.constraint_column_usage ccu "
            "  ON ccu.constraint_catalog = tc.constraint_catalog "
            " AND ccu.constraint_schema  = tc.constraint_schema "
            " AND ccu.constraint_name    = tc.constraint_name "
            "WHERE tc.constraint_type = 'FOREIGN KEY' "
            f"  AND tc.table_schema = 'table_schema' "
            f"  AND tc.table_name = '{table_name}' "
            "LIMIT 1"
        )

        def _fetch():
            return self._client.rpc("execute_sql_readonly", {"sql_query": sql}).execute()

        try:
            response = await _run_sync(_fetch)
            rows = getattr(response, "data", None) or []
            if not rows:
                return None
            row = rows[0]
            return RelacionamentoInfo(
                coluna_local=row["coluna_local"],
                referencia=f"{row['schema_ref']}.{row['tabela_ref']}.{row['coluna_ref']}",
            )
        except Exception:
            return None

    async def build_full_schema(self, user_id: str) -> list[TabelaSchema]:
        """
        Assemble the complete structural schema for a user: tables + columns + FK.

        This is the primary method called by both the API endpoint and
        build_agent_schema_context(). It NEVER fetches row data.
        """
        # Step 1: get the whitelist of tables for this user
        tables_meta = await self.get_user_tables(user_id)

        result: list[TabelaSchema] = []
        for t in tables_meta:
            table_name = t["nome_tabela"]

            # Step 2: fetch columns — safe because table_name comes from the whitelist
            colunas = await self.get_table_columns(table_name)

            # Step 3: fetch FK relationship
            relacionamento = await self.get_table_relationship(table_name)

            result.append(
                TabelaSchema(
                    nome_tabela=table_name,
                    origem_arquivo=t.get("nome_origem_arquivo"),
                    tipo_arquivo=t.get("tipo_arquivo"),
                    total_linhas=t["total_linhas"],
                    criado_em=t.get("criado_em"),
                    colunas=colunas,
                    relacionamento=relacionamento,
                )
            )

        return result
