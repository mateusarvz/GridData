"""
Use cases do módulo schema_analysis.

Segurança: cada use case valida explicitamente que o recurso pertence ao user_id
antes de qualquer leitura/escrita — não depende apenas do RLS.
"""

import io
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pandas as pd
import pyarrow.parquet as pq

from app.core.supabase import get_supabase_service_client
from app.services.fk_candidate_service import detect_fk_candidates
from app.services.gemini_schema_service import (
    ColumnInput,
    FKCandidateInput,
    TableSchemaInput,
    generate_commit_sql,
    suggest_schema,
)
from app.services.schema_stats_service import compute_table_stats
from app.services.schema_stats_service import normalize_for_postgres
from app.services.schema_stats_service import sample_dataframe_for_analysis

from app.modules.schema_analysis.application.dto import (
    ColunaSchemaDTO,
    CommitSessaoResponse,
    CriarRelacionamentoResponse,
    CriarSessaoResponse,
    EditarColunaResponse,
    EditarRelacionamentoResponse,
    GetSessaoResponse,
    InferirSchemaResponse,
    RelacionamentoDTO,
    TabelaUploadedDTO,
)

logger = logging.getLogger(__name__)

PUBLIC_SCHEMA = "public"
TABLE_SCHEMA = "table_schema"

TABLE_AUDIT_LOGS = "audit_logs"
TABLE_USERS_TABLE = "users_table"


@dataclass
class _SchemaAnalysisCache:
    session_id: str
    user_id: str
    status: str = "aguardando_analise"
    total_arquivos: int = 0
    tabelas: list[dict[str, Any]] = field(default_factory=list)
    relacionamentos: list[dict[str, Any]] = field(default_factory=list)


_SCHEMA_ANALYSIS_CACHE: dict[str, _SchemaAnalysisCache] = {}


def _get_cache(session_id: str, user_id: str | None = None) -> _SchemaAnalysisCache | None:
    cache = _SCHEMA_ANALYSIS_CACHE.get(session_id)
    if not cache:
        return None
    if user_id is not None and cache.user_id != user_id:
        return None
    return cache


def _clear_cache(session_id: str) -> None:
    _SCHEMA_ANALYSIS_CACHE.pop(session_id, None)

_SAFE_POSTGRES_TYPES = re.compile(
    r"^(VARCHAR\(\d+\)|TEXT|INT|BIGINT|SMALLINT|DECIMAL\(\d+,\s*\d+\)|NUMERIC|"
    r"BOOLEAN|DATE|TIMESTAMP WITH TIME ZONE|TIMESTAMP|UUID|JSONB|JSON|"
    r"FLOAT|DOUBLE PRECISION|SERIAL|BIGSERIAL)$",
    re.IGNORECASE,
)

_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def _from(client: Any, table: str, schema: str = PUBLIC_SCHEMA) -> Any:
    try:
        if schema == PUBLIC_SCHEMA:
            return client.from_(table)
        return client.schema(schema).from_(table)
    except Exception:
        return client.from_(f"{schema}.{table}")


def _sanitize_table_name(name: str) -> str:
    base = re.sub(r"\.[^.]+$", "", name)
    slug = re.sub(r"[^a-zA-Z0-9_]", "_", base)
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug or (not slug[0].isalpha() and slug[0] != "_"):
        slug = f"tabela_{slug}"
    return slug[:62].lower()


def _colunas_from_df(df: pd.DataFrame) -> list[dict[str, Any]]:
    return compute_table_stats(sample_dataframe_for_analysis(df))


def _read_dataframe(ext: str, buf: io.BytesIO) -> pd.DataFrame:
    if ext == "csv":
        return pd.read_csv(buf)
    if ext in ("xlsx", "xls"):
        return pd.read_excel(buf)
    if ext == "parquet":
        parquet_file = pq.ParquetFile(buf)
        if parquet_file.num_row_groups == 0:
            return pd.DataFrame()
        table = parquet_file.read()
        return table.to_pandas()
    raise ValueError(f"Formato não suportado: {ext}")


def _validar_tipo_postgres(tipo: str) -> bool:
    return bool(_SAFE_POSTGRES_TYPES.match(tipo.strip()))


def _validar_identifier(name: str) -> bool:
    return bool(_SAFE_IDENTIFIER.match(name))


def _quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _constraint_name(prefix: str, table_name: str, column_name: str) -> str:
    return f"{prefix}_{table_name}_{column_name}"[:62]


def _sql_literal(value: Any) -> str:
    value = normalize_for_postgres(value)
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, str):
        txt = value.replace("'", "''")
        return f"'{txt}'"
    if isinstance(value, (dict, list)):
        txt = json.dumps(value, ensure_ascii=False).replace("'", "''")
        return f"'{txt}'::jsonb"
    txt = str(value).replace("'", "''")
    return f"'{txt}'"


def _rows_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean_df = df.where(pd.notnull(df), None)
    return clean_df.to_dict(orient="records")


def _registrar_audit(
    client: Any,
    user_id: str,
    acao: str,
    tabela: str,
    registro_id: str | None = None,
    descricao: str = "",
) -> None:
    try:
        _from(client, TABLE_AUDIT_LOGS, PUBLIC_SCHEMA).insert([
            {
                "user_id": user_id,
                "acao": acao,
                "descricao": descricao,
                "tabela_afetada": tabela,
                "registro_id": registro_id,
            }
        ]).execute()
    except Exception as exc:
        logger.warning("Falha ao registrar audit_log: %s", exc)


def _chunked(items: list[dict[str, Any]], size: int = 500) -> list[list[dict[str, Any]]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _sample_rows(rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    if len(rows) <= limit:
        return rows
    return rows[:limit]


def _column_sample_values(rows: list[dict[str, Any]], column: str, limit: int = 10) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for row in rows:
        value = row.get(column)
        if value is None:
            continue
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        values.append(text)
        if len(values) >= limit:
            break
    return values


def _is_unique_in_rows(rows: list[dict[str, Any]], column: str) -> bool:
    values = [r.get(column) for r in rows if r.get(column) is not None]
    if not values:
        return False
    return len(values) == len(set(values))


def _heuristic_name_hint(column_name: str) -> bool:
    name = column_name.lower()
    return name == "id" or name.endswith("_id") or name.startswith("id_") or name.startswith("fk_")


def _build_commit_sql(
    user_id: str,
    session_id: str,
    tabs_data: list[dict[str, Any]],
    rels_data: list[dict[str, Any]],
    rows_by_table: dict[str, list[dict[str, Any]]],
) -> tuple[str, list[str]]:
    sql_parts: list[str] = [
        "-- DamaBox commit SQL",
        f"-- session_id: {session_id}",
        "CREATE SCHEMA IF NOT EXISTS table_schema;",
        "",
    ]

    id_to_nome: dict[str, str] = {t["id"]: t["nome_tabela_sugerido"] for t in tabs_data}
    unique_cols_by_table_id: dict[str, set[str]] = {}
    for rel in rels_data:
        destino_tab_id = rel["tabela_destino_id"]
        destino_col = rel["coluna_destino"]
        destino_rows = rows_by_table.get(destino_tab_id, [])
        if _is_unique_in_rows(destino_rows, destino_col):
            unique_cols_by_table_id.setdefault(destino_tab_id, set()).add(destino_col)

    tabelas_criadas: list[str] = []

    for tab in tabs_data:
        nome_tabela = tab["nome_tabela_sugerido"]
        if not _validar_identifier(nome_tabela):
            raise ValueError(f"Nome de tabela inválido: {nome_tabela}")

        ext = tab["nome_arquivo"].rsplit(".", 1)[-1].lower() if "." in tab["nome_arquivo"] else "csv"
        total_linhas = int(tab.get("total_linhas", 0) or 0)

        colunas = tab.get("colunas_schema", [])
        ddl_lines = [
            "row_id UUID PRIMARY KEY DEFAULT gen_random_uuid()",
            "users_table_id UUID NOT NULL REFERENCES table_schema.users_table(id) ON DELETE CASCADE",
        ]

        cols_insert: list[str] = ["users_table_id"]
        col_keys: list[str] = []
        unique_cols = unique_cols_by_table_id.get(tab["id"], set())

        for col in colunas:
            nome_col = col["nome"]
            tipo = col.get("tipo_sugerido") or col.get("tipo_bruto", "TEXT")
            if not _validar_tipo_postgres(tipo):
                tipo = "TEXT"
            nulo = "" if col.get("nulo_permitido", True) else " NOT NULL"
            unique_sql = " UNIQUE" if nome_col in unique_cols else ""
            ddl_lines.append(f"{_quote_ident(nome_col)} {tipo}{nulo}{unique_sql}")
            cols_insert.append(_quote_ident(nome_col))
            col_keys.append(nome_col)

        create_table_sql = (
            f"CREATE TABLE IF NOT EXISTS table_schema.{_quote_ident(nome_tabela)} (\n  "
            + ",\n  ".join(ddl_lines)
            + "\n);"
        )

        sql_parts.append(
            "\n".join([
                "DO $$",
                "DECLARE",
                "  v_users_table_id UUID;",
                "BEGIN",
                "  INSERT INTO table_schema.users_table (user_id, nome_tabela, nome_origem_arquivo, tipo_arquivo, total_linhas)",
                f"  VALUES ({_sql_literal(user_id)}, {_sql_literal(nome_tabela)}, {_sql_literal(tab['nome_arquivo'])}, {_sql_literal(ext)}, {total_linhas})",
                "  RETURNING id INTO v_users_table_id;",
                "",
                f"  {create_table_sql}",
                "",
                "END $$;",
                "",
            ]).strip()
        )

        rows = rows_by_table.get(tab["id"], [])
        for chunk_index, chunk in enumerate(_chunked(rows, size=100), start=1):
            values_sql = []
            for row in chunk:
                vals = ["v_users_table_id"]
                for key in col_keys:
                    vals.append(_sql_literal(row.get(key)))
                values_sql.append("(" + ", ".join(vals) + ")")

            if not values_sql:
                continue

            insert_rows_sql = (
                f"INSERT INTO table_schema.{_quote_ident(nome_tabela)} ({', '.join(cols_insert)}) VALUES\n  "
                + ",\n  ".join(values_sql)
                + ";"
            )
            sql_parts.append(
                "\n".join([
                    "DO $$",
                    "DECLARE",
                    "  v_users_table_id UUID;",
                    "BEGIN",
                    f"  SELECT id INTO v_users_table_id FROM table_schema.users_table WHERE user_id = {_sql_literal(user_id)} AND nome_tabela = {_sql_literal(nome_tabela)} ORDER BY criado_em DESC LIMIT 1;",
                    "",
                    f"  {insert_rows_sql.replace('\n', '\n  ')}",
                    "END $$;",
                    "",
                ]).strip()
            )

        tabelas_criadas.append(nome_tabela)

    for rel in rels_data:
        origem_nome = id_to_nome.get(rel["tabela_origem_id"])
        destino_nome = id_to_nome.get(rel["tabela_destino_id"])
        if not origem_nome or not destino_nome:
            continue
        origem_col = rel["coluna_origem"]
        destino_col = rel["coluna_destino"]

        destino_tab_id = rel["tabela_destino_id"]
        unique_cols = unique_cols_by_table_id.get(destino_tab_id, set())
        if destino_col not in unique_cols:
            logger.warning(
                "Relacionamento ignorado por coluna de destino não única: %s.%s -> %s.%s",
                origem_nome,
                origem_col,
                destino_nome,
                destino_col,
            )
            continue

        constraint_name = _constraint_name("fk", origem_nome, f"{origem_col}_{destino_nome}")

        sql_parts.append(
            f"ALTER TABLE table_schema.{_quote_ident(origem_nome)} "
            f"DROP CONSTRAINT IF EXISTS {_quote_ident(constraint_name)};"
        )
        sql_parts.append(
            f"ALTER TABLE table_schema.{_quote_ident(origem_nome)} "
            f"ADD CONSTRAINT {_quote_ident(constraint_name)} "
            f"FOREIGN KEY ({_quote_ident(origem_col)}) "
            f"REFERENCES table_schema.{_quote_ident(destino_nome)} ({_quote_ident(destino_col)});"
        )
        sql_parts.append("")

    return "\n".join(sql_parts).strip(), tabelas_criadas


def _execute_sql_via_rpc(client: Any, sql: str) -> None:
    try:
        res = client.rpc("execute_sql", {"sql_query": sql}).execute()
        err = getattr(res, "error", None)
        if err:
            raise RuntimeError(str(err))
        return
    except Exception as exc:
        # Cache stale do PostgREST pode não enxergar assinatura mais recente da RPC.
        if "PGRST202" in str(exc):
            try:
                client.rpc("execute_sql", {"sql_query": "SELECT pg_notify('pgrst', 'reload schema')"}).execute()
                client.rpc("execute_sql", {"sql_query": "SELECT pg_notify('pgrst', 'reload config')"}).execute()
                res = client.rpc("execute_sql", {"sql_query": sql}).execute()
                err = getattr(res, "error", None)
                if err:
                    raise RuntimeError(str(err))
                return
            except Exception as reload_exc:
                raise RuntimeError(str(reload_exc)) from reload_exc
        raise RuntimeError(str(exc)) from exc


def _friendly_commit_error(exc: Exception, nome_tabela: str | None = None) -> str:
    text = str(exc)
    if "users_table_user_id_nome_tabela_key" in text or "'code': '23505'" in text or "duplicate key value violates unique constraint" in text:
        if nome_tabela:
            return f"Já existe uma tabela com nome '{nome_tabela}' para este usuário. Renomeie a tabela ou remova a anterior antes de inserir novamente."
        return "Já existe uma tabela com esse mesmo nome para este usuário. Renomeie a tabela ou remova a anterior antes de inserir novamente."
    return f"Falha ao executar SQL de commit: {text}"


class CriarSessaoUseCase:
    async def execute(self, user_id: str, files: list[tuple[str, bytes]], nome_usuario: str = "") -> CriarSessaoResponse:
        client = get_supabase_service_client()
        if client is None:
            return CriarSessaoResponse(ok=False, error="Supabase service_role não configurado.")

        try:
            session_id = str(uuid4())
            _SCHEMA_ANALYSIS_CACHE[session_id] = _SchemaAnalysisCache(
                session_id=session_id,
                user_id=user_id,
                status="aguardando_analise",
                total_arquivos=len(files),
            )
            tabelas: list[TabelaUploadedDTO] = []

            for file_name, content in files:
                try:
                    ext = file_name.rsplit(".", 1)[-1].lower()
                    buf = io.BytesIO(content)
                    full_df = _read_dataframe(ext, buf)
                    analysis_df = sample_dataframe_for_analysis(full_df)

                    colunas = _colunas_from_df(analysis_df)
                    nome_tabela = _sanitize_table_name(file_name)
                    if nome_usuario:
                        safe_user = _sanitize_table_name(nome_usuario)
                        if safe_user:
                            nome_tabela = f"{nome_tabela}_{safe_user}"

                    table_id = str(uuid4())
                    cache = _get_cache(session_id, user_id)
                    if cache is None:
                        return CriarSessaoResponse(ok=False, error="Falha ao criar sessão temporária.")
                    cache.tabelas.append(
                        {
                            "id": table_id,
                            "nome_arquivo": file_name,
                            "nome_tabela_sugerido": nome_tabela,
                            "colunas_schema": colunas,
                            "total_linhas": int(full_df.shape[0]),
                        }
                    )
                    rows = _rows_to_records(full_df)
                    cache_rows = cache.__dict__.setdefault("rows_by_table", {})
                    cache_rows[table_id] = rows

                    tabelas.append(
                        TabelaUploadedDTO(
                            table_id=table_id,
                            nome_arquivo=file_name,
                            nome_tabela_sugerido=nome_tabela,
                            total_linhas=int(full_df.shape[0]),
                            colunas=[ColunaSchemaDTO(**c) for c in colunas],
                        )
                    )
                except Exception as exc:
                    logger.warning("Erro ao processar arquivo %s: %s", file_name, exc)

            _registrar_audit(
                client,
                user_id,
                "criar_sessao_analise",
                "schema_analysis_cache",
                session_id,
                f"Sessão criada com {len(files)} arquivo(s)",
            )

            return CriarSessaoResponse(ok=True, session_id=session_id, tabelas=tabelas)
        except Exception as exc:
            logger.exception("CriarSessaoUseCase erro: %s", exc)
            return CriarSessaoResponse(ok=False, error=str(exc))


class InferirSchemaUseCase:
    async def execute(self, user_id: str, session_id: str) -> InferirSchemaResponse:
        cache = _get_cache(session_id, user_id)
        if not cache:
            return InferirSchemaResponse(ok=False, error="Sessão não encontrada ou acesso negado.")

        infer_relationships = int(cache.total_arquivos or 0) > 1
        tabs_data = cache.tabelas
        if not tabs_data:
            return InferirSchemaResponse(ok=False, error="Nenhuma tabela encontrada na sessão.")

        gemini_inputs: list[TableSchemaInput] = []
        tables_for_fk: list[dict[str, Any]] = []

        for tab in tabs_data:
            colunas_raw: list[dict[str, Any]] = tab.get("colunas_schema", [])
            rows_tab = getattr(cache, "rows_by_table", {}).get(tab["id"], []) if hasattr(cache, "rows_by_table") else []
            colunas_input = [
                ColumnInput(
                    nome=c["nome"],
                    tipo_bruto=c.get("tipo_bruto", "object"),
                    total_linhas=tab.get("total_linhas", 0),
                    valores_nulos=c.get("valores_nulos", 0),
                    percentual_nulos=c.get("percentual_nulos", 0.0),
                    valores_unicos=c.get("valores_unicos", 0),
                    percentual_unicidade=c.get("percentual_unicidade", 0.0),
                    is_pk_candidate=c.get("is_pk_candidate", False),
                    exemplos_gemini=c.get("exemplos_gemini") or [],
                )
                for c in colunas_raw
            ]
            gemini_inputs.append(
                TableSchemaInput(
                    nome_tabela=tab["nome_tabela_sugerido"],
                    nome_arquivo=tab["nome_arquivo"],
                    table_id=tab["id"],
                    colunas=colunas_input,
                )
            )

            tables_for_fk.append(
                {
                    "nome_tabela": tab["nome_tabela_sugerido"],
                    "colunas": [
                        {
                            "nome": c["nome"],
                            "is_pk_candidate": c.get("is_pk_candidate", False),
                            "amostra_fk": _column_sample_values(rows_tab, c["nome"], 10),
                            "is_unique": _is_unique_in_rows(rows_tab, c["nome"]),
                        }
                        for c in colunas_raw
                    ],
                }
            )

        fk_candidatos_raw = detect_fk_candidates(tables_for_fk) if infer_relationships else []
        fk_candidates_input = [
            FKCandidateInput(
                tabela_origem=c.tabela_origem,
                coluna_origem=c.coluna_origem,
                tabela_destino=c.tabela_destino,
                coluna_destino=c.coluna_destino,
                percentual_sobreposicao=c.percentual_sobreposicao,
                percentual_sobreposicao_inversa=c.percentual_sobreposicao_inversa,
                unica_origem=c.unica_origem,
                unica_destino=c.unica_destino,
                compatibilidade_nome=c.compatibilidade_nome,
                mesmo_nome=c.mesmo_nome,
                cardinalidade=c.cardinalidade,
                score=c.score,
                valores_origem_amostra=c.valores_origem_amostra,
                valores_destino_amostra=c.valores_destino_amostra,
            )
            for c in fk_candidatos_raw
        ]

        sugestao = await suggest_schema(gemini_inputs, infer_relationships, fk_candidates_input)
        gemini_usado = settings_gemini_available()

        tabelas_dto: list[TabelaUploadedDTO] = []
        id_to_nome: dict[str, str] = {}

        for tab in tabs_data:
            tab_id = tab["id"]
            nome_tabela = tab["nome_tabela_sugerido"]
            id_to_nome[tab_id] = nome_tabela

            sugestoes_cols = sugestao.tabelas.get(nome_tabela, [])
            tipo_map = {s.nome: s.tipo_sugerido for s in sugestoes_cols}

            colunas_atualizadas: list[dict[str, Any]] = []
            for c in tab.get("colunas_schema", []):
                c_copy = dict(c)
                tipo_local = c.get("tipo_sugerido", "") or c.get("tipo_bruto", "TEXT")
                tipo_gemini = tipo_map.get(c["nome"], "") or tipo_local
                c_copy["tipo_sugerido"] = tipo_local if tipo_gemini.upper() == "TEXT" and tipo_local.upper() != "TEXT" else tipo_gemini
                colunas_atualizadas.append(c_copy)

            for cache_tab in cache.tabelas:
                if cache_tab["id"] == tab_id:
                    cache_tab["colunas_schema"] = colunas_atualizadas
                    break

            tabelas_dto.append(
                TabelaUploadedDTO(
                    table_id=tab_id,
                    nome_arquivo=tab["nome_arquivo"],
                    nome_tabela_sugerido=nome_tabela,
                    total_linhas=tab.get("total_linhas", 0),
                    colunas=[ColunaSchemaDTO(**c) for c in colunas_atualizadas],
                )
            )

        relacionamentos_dto: list[RelacionamentoDTO] = []
        nome_to_id = {v: k for k, v in id_to_nome.items()}
        cache.relacionamentos = []

        for rel in sugestao.relacionamentos:
            origem_id = nome_to_id.get(rel.tabela_origem)
            destino_id = nome_to_id.get(rel.tabela_destino)
            if not origem_id or not destino_id:
                continue
            if rel.acao == "rejeita":
                continue

            rel_tipo = rel.tipo_relacionamento
            if rel.acao == "ajusta" and rel.ajuste:
                origem_id = nome_to_id.get(rel.ajuste.get("tabela_origem", rel.tabela_origem), origem_id)
                destino_id = nome_to_id.get(rel.ajuste.get("tabela_destino", rel.tabela_destino), destino_id)
                rel_tipo = rel.ajuste.get("tipo_relacionamento", rel_tipo)
                rel_col_origem = rel.ajuste.get("coluna_origem", rel.coluna_origem)
                rel_col_destino = rel.ajuste.get("coluna_destino", rel.coluna_destino)
            else:
                rel_col_origem = rel.coluna_origem
                rel_col_destino = rel.coluna_destino
            if rel_tipo == "N:1":
                rel_tipo = "1:N"

            origem_rel = "gemini"
            rel_id = str(uuid4())
            aprovado = True
            cache.relacionamentos.append(
                {
                    "id": rel_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "tabela_origem_id": origem_id,
                    "coluna_origem": rel_col_origem,
                    "tabela_destino_id": destino_id,
                    "coluna_destino": rel_col_destino,
                    "tipo_relacionamento": rel_tipo,
                    "grau_confianca": rel.grau_confianca,
                    "origem": origem_rel,
                "aprovado": aprovado,
                    "justificativa": rel.justificativa,
                    "acao_gemini": rel.acao,
                }
            )

            relacionamentos_dto.append(
                RelacionamentoDTO(
                    id=rel_id,
                    tabela_origem_id=origem_id,
                    coluna_origem=rel_col_origem,
                    tabela_destino_id=destino_id,
                    coluna_destino=rel_col_destino,
                    tipo_relacionamento=rel_tipo,
                    grau_confianca=rel.grau_confianca,
                    origem=origem_rel,
                    aprovado=aprovado,
                    justificativa=rel.justificativa,
                    nome_tabela_origem=rel.tabela_origem,
                    nome_tabela_destino=rel.tabela_destino,
                    acao_gemini=rel.acao,
                )
            )

        cache.status = "analisado"

        client = get_supabase_service_client()
        if client is not None:
            _registrar_audit(
                client,
                user_id,
                "inferir_schema_gemini",
                "schema_analysis_cache",
                session_id,
                f"Gemini inferiu {len(tabs_data)} tabela(s), {len(relacionamentos_dto)} relacionamento(s)",
            )

        return InferirSchemaResponse(
            ok=True,
            session_id=session_id,
            tabelas=tabelas_dto,
            relacionamentos=relacionamentos_dto,
            gemini_usado=gemini_usado,
        )


def settings_gemini_available() -> bool:
    try:
        from app.core.config import settings

        return bool(settings.GEMINI_API_KEY_EFFECTIVE)
    except Exception:
        return False


class GetSessaoUseCase:
    async def execute(self, user_id: str, session_id: str) -> GetSessaoResponse:
        cache = _get_cache(session_id, user_id)
        if not cache:
            return GetSessaoResponse(ok=False, error="Sessão não encontrada ou acesso negado.")

        tabelas: list[TabelaUploadedDTO] = []
        id_to_nome: dict[str, str] = {}
        for tab in cache.tabelas:
            id_to_nome[tab["id"]] = tab["nome_tabela_sugerido"]
            colunas_dto = [
                ColunaSchemaDTO(
                    nome=c["nome"],
                    tipo_bruto=c.get("tipo_bruto", "object"),
                    tipo_sugerido=c.get("tipo_sugerido", ""),
                    nulo_permitido=c.get("nulo_permitido", True),
                    editado_pelo_usuario=c.get("editado_pelo_usuario", False),
                )
                for c in tab.get("colunas_schema", [])
            ]
            tabelas.append(
                TabelaUploadedDTO(
                    table_id=tab["id"],
                    nome_arquivo=tab["nome_arquivo"],
                    nome_tabela_sugerido=tab["nome_tabela_sugerido"],
                    total_linhas=tab.get("total_linhas", 0),
                    colunas=colunas_dto,
                )
            )

        relacionamentos = [
            RelacionamentoDTO(
                id=r["id"],
                tabela_origem_id=r["tabela_origem_id"],
                coluna_origem=r["coluna_origem"],
                tabela_destino_id=r["tabela_destino_id"],
                coluna_destino=r["coluna_destino"],
                tipo_relacionamento=r.get("tipo_relacionamento", "1:N"),
                grau_confianca=float(r.get("grau_confianca", 1.0)),
                origem=r.get("origem", "gemini"),
                aprovado=bool(r.get("aprovado", float(r.get("grau_confianca", 1.0)) >= 1.0))
                if float(r.get("grau_confianca", 1.0)) >= 1.0
                else False,
                justificativa=r.get("justificativa") or "",
                nome_tabela_origem=id_to_nome.get(r["tabela_origem_id"], ""),
                nome_tabela_destino=id_to_nome.get(r["tabela_destino_id"], ""),
            )
            for r in cache.relacionamentos
        ]

        return GetSessaoResponse(
            ok=True,
            session_id=session_id,
            status=cache.status,
            total_arquivos=cache.total_arquivos,
            tabelas=tabelas,
            relacionamentos=relacionamentos,
        )


class EditarColunaUseCase:
    async def execute(
        self,
        user_id: str,
        session_id: str,
        table_id: str,
        column_name: str,
        novo_tipo: str,
    ) -> EditarColunaResponse:
        if not _validar_tipo_postgres(novo_tipo):
            return EditarColunaResponse(ok=False, error=f"Tipo Postgres inválido: {novo_tipo}")

        cache = _get_cache(session_id, user_id)
        if not cache:
            return EditarColunaResponse(ok=False, error="Tabela não encontrada ou acesso negado.")

        col_found = False
        for tab in cache.tabelas:
            if tab["id"] != table_id:
                continue
            colunas: list[dict[str, Any]] = tab.get("colunas_schema", [])
            for c in colunas:
                if c["nome"] == column_name:
                    c["tipo_sugerido"] = novo_tipo
                    c["editado_pelo_usuario"] = True
                    col_found = True
                    break
            if col_found:
                break

        if not col_found:
            return EditarColunaResponse(ok=False, error=f"Coluna '{column_name}' não encontrada.")

        client = get_supabase_service_client()
        if client is not None:
            _registrar_audit(
                client,
                user_id,
                "editar_tipo_coluna",
                "schema_analysis_cache",
                table_id,
                f"Coluna '{column_name}' => '{novo_tipo}'",
            )

        return EditarColunaResponse(ok=True)


class EditarNuloColunaUseCase:
    async def execute(
        self,
        user_id: str,
        session_id: str,
        table_id: str,
        column_name: str,
        nulo_permitido: bool,
    ) -> EditarColunaResponse:
        cache = _get_cache(session_id, user_id)
        if not cache:
            return EditarColunaResponse(ok=False, error="Tabela não encontrada ou acesso negado.")

        col_found = False
        for tab in cache.tabelas:
            if tab["id"] != table_id:
                continue
            colunas: list[dict[str, Any]] = tab.get("colunas_schema", [])
            for c in colunas:
                if c["nome"] == column_name:
                    c["nulo_permitido"] = nulo_permitido
                    c["editado_pelo_usuario"] = True
                    col_found = True
                    break
            if col_found:
                break

        if not col_found:
            return EditarColunaResponse(ok=False, error=f"Coluna '{column_name}' não encontrada.")

        client = get_supabase_service_client()
        if client is not None:
            _registrar_audit(
                client,
                user_id,
                "editar_nulo_coluna",
                "schema_analysis_cache",
                table_id,
                f"Coluna '{column_name}' => nulo_permitido={nulo_permitido}",
            )

        return EditarColunaResponse(ok=True)


class CriarRelacionamentoUseCase:
    async def execute(
        self,
        user_id: str,
        session_id: str,
        tabela_origem_id: str,
        coluna_origem: str,
        tabela_destino_id: str,
        coluna_destino: str,
        tipo_relacionamento: str,
    ) -> CriarRelacionamentoResponse:
        if tipo_relacionamento not in ("1:1", "1:N", "N:N"):
            return CriarRelacionamentoResponse(ok=False, error="Tipo de relacionamento inválido.")

        cache = _get_cache(session_id, user_id)
        if not cache:
            return CriarRelacionamentoResponse(ok=False, error="Sessão não encontrada ou acesso negado.")

        rel_id = str(uuid4())
        cache.relacionamentos.append(
            {
                "id": rel_id,
                "tabela_origem_id": tabela_origem_id,
                "coluna_origem": coluna_origem,
                "tabela_destino_id": tabela_destino_id,
                "coluna_destino": coluna_destino,
                "tipo_relacionamento": tipo_relacionamento,
                "grau_confianca": 1.0,
                "origem": "usuario",
                "aprovado": True,
                "justificativa": "",
            }
        )

        client = get_supabase_service_client()
        if client is not None:
            _registrar_audit(client, user_id, "criar_relacionamento_manual", "schema_analysis_cache", rel_id)

        return CriarRelacionamentoResponse(
            ok=True,
            relacionamento=RelacionamentoDTO(
                id=rel_id,
                tabela_origem_id=tabela_origem_id,
                coluna_origem=coluna_origem,
                tabela_destino_id=tabela_destino_id,
                coluna_destino=coluna_destino,
                tipo_relacionamento=tipo_relacionamento,
                origem="usuario",
                aprovado=True,
            ),
        )


class EditarRelacionamentoUseCase:
    async def execute(
        self,
        user_id: str,
        session_id: str,
        relationship_id: str,
        aprovado: bool | None,
        tipo_relacionamento: str | None,
    ) -> EditarRelacionamentoResponse:
        cache = _get_cache(session_id, user_id)
        if not cache:
            return EditarRelacionamentoResponse(ok=False, error="Relacionamento não encontrado ou acesso negado.")

        rel = next((r for r in cache.relacionamentos if r["id"] == relationship_id), None)
        if not rel:
            return EditarRelacionamentoResponse(ok=False, error="Relacionamento não encontrado ou acesso negado.")

        if aprovado is not None:
            rel["aprovado"] = aprovado
        if tipo_relacionamento is not None:
            if tipo_relacionamento not in ("1:1", "1:N", "N:N"):
                return EditarRelacionamentoResponse(ok=False, error="Tipo de relacionamento inválido.")
            rel["tipo_relacionamento"] = tipo_relacionamento

        client = get_supabase_service_client()
        if client is not None:
            _registrar_audit(client, user_id, "editar_relacionamento", "schema_analysis_cache", relationship_id)
        return EditarRelacionamentoResponse(ok=True)


class CommitSessaoUseCase:
    def _validate_null_constraints(
        self,
        tabs_data: list[dict[str, Any]],
        rows_by_table: dict[str, list[dict[str, Any]]],
    ) -> str | None:
        for tab in tabs_data:
            rows = rows_by_table.get(tab["id"], [])
            for col in tab.get("colunas_schema", []):
                if col.get("nulo_permitido", True):
                    continue
                col_name = col["nome"]
                if any(row.get(col_name) is None for row in rows):
                    return (
                        f"A coluna '{col_name}' não permite nulos, mas existem valores vazios nos dados enviados. "
                        "Marque 'Permite nulo' como 'Sim' ou preencha a coluna antes de inserir no Supabase."
                    )
        return None

    async def execute(self, user_id: str, session_id: str) -> CommitSessaoResponse:
        client = get_supabase_service_client()
        cache = _get_cache(session_id, user_id)
        if not cache:
            return CommitSessaoResponse(ok=False, error="Sessão não encontrada ou acesso negado.")

        if cache.status == "confirmado":
            return CommitSessaoResponse(ok=False, error="Sessão já foi confirmada.")

        tabs_data = cache.tabelas
        if not tabs_data:
            return CommitSessaoResponse(ok=False, error="Nenhuma tabela para commit.")

        rels_data = [r for r in cache.relacionamentos if r.get("aprovado", True)]

        rows_by_table: dict[str, list[dict[str, Any]]] = {}
        rows_by_table = getattr(cache, "rows_by_table", {}) or {}

        null_error = self._validate_null_constraints(tabs_data, rows_by_table)
        if null_error:
            return CommitSessaoResponse(ok=False, error=null_error)

        # Gera SQL determinístico
        try:
            fallback_sql, tabelas_criadas = _build_commit_sql(user_id, session_id, tabs_data, rels_data, rows_by_table)
        except Exception as exc:
            return CommitSessaoResponse(ok=False, error=str(exc))

        # Segunda chamada Gemini para refinar SQL de commit
        prompt_context = json.dumps(
            {
                "session_id": session_id,
                "tables": [
                    {
                        "nome_tabela": t["nome_tabela_sugerido"],
                        "nome_arquivo": t["nome_arquivo"],
                        "total_linhas": t.get("total_linhas", 0),
                        "colunas_schema": t.get("colunas_schema", []),
                        "rows_sample": _sample_rows(rows_by_table.get(t["id"], []), 20),
                        "rows_total": len(rows_by_table.get(t["id"], [])),
                    }
                    for t in tabs_data
                ],
                "relacionamentos_aprovados": rels_data,
                "rules": {
                    "target_schema": TABLE_SCHEMA,
                    "owner_table": "table_schema.users_table",
                    "owner_fk_column": "users_table_id",
                },
            },
            ensure_ascii=False,
            default=str,
        )
        total_rows = sum(len(rows_by_table.get(t["id"], [])) for t in tabs_data)
        sql_final = fallback_sql
        if total_rows <= 2000:
            sql_final = await generate_commit_sql(prompt_context, fallback_sql)

        # Executar SQL no Supabase via RPC
        try:
            _execute_sql_via_rpc(client, sql_final)
        except Exception as exc:
            logger.exception("Erro ao executar SQL de commit via RPC: %s", exc)
            nome_tabela_erro: str | None = None
            for tab in tabs_data:
                if tab["nome_tabela_sugerido"] in str(exc):
                    nome_tabela_erro = tab["nome_tabela_sugerido"]
                    break
            return CommitSessaoResponse(ok=False, sql_gerado=sql_final, error=_friendly_commit_error(exc, nome_tabela_erro))

        # Limpeza de staging
        cache.status = "confirmado"
        _clear_cache(session_id)

        if client is not None:
            _registrar_audit(
                client,
                user_id,
                "commit_schema",
                "schema_analysis_cache",
                session_id,
                f"Commit realizado: {len(tabelas_criadas)} tabela(s) criadas em table_schema",
            )

        return CommitSessaoResponse(ok=True, sql_gerado=sql_final, tabelas_criadas=tabelas_criadas)
