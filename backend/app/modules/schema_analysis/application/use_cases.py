"""
Use cases do módulo schema_analysis.

Segurança: cada use case valida explicitamente que o recurso pertence ao user_id
antes de qualquer leitura/escrita — não depende apenas do RLS.
"""

import io
import re
import json
import logging
from datetime import date, timedelta
from typing import Any

import pandas as pd

from app.core.supabase import get_supabase_service_client
from app.services.gemini_schema_service import (
    TableSchemaInput,
    ColumnInput,
    suggest_schema,
)
from app.modules.schema_analysis.application.dto import (
    ColunaSchemaDTO,
    TabelaUploadedDTO,
    RelacionamentoDTO,
    CriarSessaoResponse,
    InferirSchemaResponse,
    GetSessaoResponse,
    EditarColunaResponse,
    CriarRelacionamentoResponse,
    EditarRelacionamentoResponse,
    CommitSessaoResponse,
)

logger = logging.getLogger(__name__)

# Tipos Postgres permitidos no commit final
_SAFE_POSTGRES_TYPES = re.compile(
    r"^(VARCHAR\(\d+\)|TEXT|INT|BIGINT|SMALLINT|DECIMAL\(\d+,\s*\d+\)|NUMERIC|"
    r"BOOLEAN|DATE|TIMESTAMP WITH TIME ZONE|TIMESTAMP|UUID|JSONB|JSON|"
    r"FLOAT|DOUBLE PRECISION|SERIAL|BIGSERIAL)$",
    re.IGNORECASE,
)

_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def _sanitize_table_name(name: str) -> str:
    """Converte nome de arquivo em nome de tabela válido."""
    base = re.sub(r"\.[^.]+$", "", name)          # remove extensão
    slug = re.sub(r"[^a-zA-Z0-9_]", "_", base)    # substitui caracteres inválidos
    slug = re.sub(r"_+", "_", slug).strip("_")     # colapsa underscores
    if not slug or not slug[0].isalpha() and slug[0] != "_":
        slug = "tabela_" + slug
    return slug[:62].lower()


def _infer_tipo_bruto(dtype: Any) -> str:
    return str(dtype)


def _colunas_from_df(df: pd.DataFrame) -> list[dict]:
    """Gera lista de colunas com tipo_bruto a partir de um DataFrame."""
    return [
        {
            "nome": col,
            "tipo_bruto": _infer_tipo_bruto(df[col].dtype),
            "tipo_sugerido": "",
            "nulo_permitido": bool(df[col].isnull().any()),
            "editado_pelo_usuario": False,
        }
        for col in df.columns
    ]


def _exemplos_seguros(df: pd.DataFrame, col: str) -> list[Any]:
    """Extrai até 3 exemplos não-nulos de uma coluna, convertidos para string."""
    try:
        vals = df[col].dropna().head(3).tolist()
        return [str(v) for v in vals]
    except Exception:
        return []


def _validar_tipo_postgres(tipo: str) -> bool:
    return bool(_SAFE_POSTGRES_TYPES.match(tipo.strip()))


def _validar_identifier(name: str) -> bool:
    return bool(_SAFE_IDENTIFIER.match(name))


def _registrar_audit(client: Any, user_id: str, acao: str, tabela: str, registro_id: str | None = None, descricao: str = "") -> None:
    try:
        client.from_("audit_logs").insert([{
            "user_id": user_id,
            "acao": acao,
            "descricao": descricao,
            "tabela_afetada": tabela,
            "registro_id": registro_id,
        }]).execute()
    except Exception as exc:
        logger.warning("Falha ao registrar audit_log: %s", exc)


# ---------------------------------------------------------------------------
# Use Case 1: Criar sessão e fazer upload dos arquivos
# ---------------------------------------------------------------------------

class CriarSessaoUseCase:
    async def execute(
        self,
        user_id: str,
        files: list[tuple[str, bytes]],
    ) -> CriarSessaoResponse:
        client = get_supabase_service_client()
        if client is None:
            return CriarSessaoResponse(ok=False, error="Supabase service_role não configurado.")

        try:
            # 1. Criar sessão
            sess_res = (
                client.from_("schema_analysis_sessions")
                .insert([{
                    "user_id": user_id,
                    "status": "aguardando_analise",
                    "total_arquivos": len(files),
                }])
                .select("id")
                .execute()
            )
            sess_data = getattr(sess_res, "data", None)
            if not sess_data:
                return CriarSessaoResponse(ok=False, error="Falha ao criar sessão.")

            session_id = sess_data[0]["id"]

            # 2. Para cada arquivo: parsear e gravar metadados
            tabelas: list[TabelaUploadedDTO] = []
            for file_name, content in files:
                try:
                    ext = file_name.rsplit(".", 1)[-1].lower()
                    buf = io.BytesIO(content)
                    if ext == "csv":
                        df = pd.read_csv(buf)
                    elif ext == "parquet":
                        df = pd.read_parquet(buf)
                    elif ext in ("xlsx", "xls"):
                        df = pd.read_excel(buf)
                    else:
                        continue

                    colunas = _colunas_from_df(df)
                    nome_tabela = _sanitize_table_name(file_name)

                    tab_res = (
                        client.from_("schema_analysis_tables")
                        .insert([{
                            "session_id": session_id,
                            "user_id": user_id,
                            "nome_arquivo": file_name,
                            "nome_tabela_sugerido": nome_tabela,
                            "colunas_schema": colunas,
                            "total_linhas": int(df.shape[0]),
                        }])
                        .select("id")
                        .execute()
                    )
                    tab_data = getattr(tab_res, "data", None)
                    if not tab_data:
                        continue

                    tabelas.append(TabelaUploadedDTO(
                        table_id=tab_data[0]["id"],
                        nome_arquivo=file_name,
                        nome_tabela_sugerido=nome_tabela,
                        total_linhas=int(df.shape[0]),
                        colunas=[ColunaSchemaDTO(**c) for c in colunas],
                    ))
                except Exception as exc:
                    logger.warning("Erro ao processar arquivo %s: %s", file_name, exc)
                    continue

            _registrar_audit(
                client, user_id, "criar_sessao_analise",
                "schema_analysis_sessions", session_id,
                f"Sessão criada com {len(files)} arquivo(s)",
            )

            return CriarSessaoResponse(
                ok=True,
                session_id=session_id,
                tabelas=tabelas,
            )

        except Exception as exc:
            logger.exception("CriarSessaoUseCase erro: %s", exc)
            return CriarSessaoResponse(ok=False, error=str(exc))


# ---------------------------------------------------------------------------
# Use Case 2: Inferir tipos e relacionamentos via Gemini
# ---------------------------------------------------------------------------

class InferirSchemaUseCase:
    async def execute(self, user_id: str, session_id: str) -> InferirSchemaResponse:
        client = get_supabase_service_client()
        if client is None:
            return InferirSchemaResponse(ok=False, error="Supabase service_role não configurado.")

        # Validar posse da sessão
        sess_res = (
            client.from_("schema_analysis_sessions")
            .select("id, total_arquivos, status")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        sess = getattr(sess_res, "data", None)
        if not sess:
            return InferirSchemaResponse(ok=False, error="Sessão não encontrada ou acesso negado.")

        total_arquivos = sess.get("total_arquivos", 0)
        infer_relationships = total_arquivos > 1

        # Buscar tabelas da sessão
        tabs_res = (
            client.from_("schema_analysis_tables")
            .select("id, nome_arquivo, nome_tabela_sugerido, colunas_schema, total_linhas")
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        tabs_data = getattr(tabs_res, "data", []) or []

        if not tabs_data:
            return InferirSchemaResponse(ok=False, error="Nenhuma tabela encontrada na sessão.")

        # Montar input para Gemini (apenas metadados)
        gemini_inputs: list[TableSchemaInput] = []
        for tab in tabs_data:
            colunas_raw: list[dict] = tab.get("colunas_schema", [])
            colunas_input = [
                ColumnInput(
                    nome=c["nome"],
                    tipo_bruto=c.get("tipo_bruto", "object"),
                    total_linhas=tab.get("total_linhas", 0),
                    exemplos=[],  # Exemplos não são coletados no upload — segurança
                )
                for c in colunas_raw
            ]
            gemini_inputs.append(TableSchemaInput(
                nome_tabela=tab["nome_tabela_sugerido"],
                nome_arquivo=tab["nome_arquivo"],
                table_id=tab["id"],
                colunas=colunas_input,
            ))

        # Chamar Gemini
        sugestao = await suggest_schema(gemini_inputs, infer_relationships)
        gemini_usado = bool(settings_gemini_available())

        # Persistir sugestões de tipos nas colunas_schema
        tabelas_dto: list[TabelaUploadedDTO] = []
        id_to_nome: dict[str, str] = {}

        for tab in tabs_data:
            tab_id = tab["id"]
            nome_tabela = tab["nome_tabela_sugerido"]
            id_to_nome[tab_id] = nome_tabela

            sugestoes_cols = sugestao.tabelas.get(nome_tabela, [])
            tipo_map = {s.nome: s.tipo_sugerido for s in sugestoes_cols}

            colunas_raw: list[dict] = tab.get("colunas_schema", [])
            colunas_atualizadas = []
            for c in colunas_raw:
                c_copy = dict(c)
                c_copy["tipo_sugerido"] = tipo_map.get(c["nome"], "") or c.get("tipo_bruto", "TEXT")
                colunas_atualizadas.append(c_copy)

            client.from_("schema_analysis_tables").update({
                "colunas_schema": colunas_atualizadas,
            }).eq("id", tab_id).execute()

            tabelas_dto.append(TabelaUploadedDTO(
                table_id=tab_id,
                nome_arquivo=tab["nome_arquivo"],
                nome_tabela_sugerido=nome_tabela,
                total_linhas=tab.get("total_linhas", 0),
                colunas=[ColunaSchemaDTO(**c) for c in colunas_atualizadas],
            ))

        # Persistir relacionamentos sugeridos
        relacionamentos_dto: list[RelacionamentoDTO] = []
        nome_to_id = {v: k for k, v in id_to_nome.items()}

        for rel in sugestao.relacionamentos:
            origem_id = nome_to_id.get(rel.tabela_origem)
            destino_id = nome_to_id.get(rel.tabela_destino)
            if not origem_id or not destino_id:
                continue

            # Valida que ambas as tabelas pertencem ao user_id (já verificadas acima)
            rel_res = (
                client.from_("schema_analysis_relationships")
                .insert([{
                    "session_id": session_id,
                    "user_id": user_id,
                    "tabela_origem_id": origem_id,
                    "coluna_origem": rel.coluna_origem,
                    "tabela_destino_id": destino_id,
                    "coluna_destino": rel.coluna_destino,
                    "tipo_relacionamento": rel.tipo_relacionamento,
                    "grau_confianca": rel.grau_confianca,
                    "origem": "gemini",
                    "aprovado": True,
                }])
                .select("id")
                .execute()
            )
            rel_data = getattr(rel_res, "data", None)
            rel_id = rel_data[0]["id"] if rel_data else None

            relacionamentos_dto.append(RelacionamentoDTO(
                id=rel_id,
                tabela_origem_id=origem_id,
                coluna_origem=rel.coluna_origem,
                tabela_destino_id=destino_id,
                coluna_destino=rel.coluna_destino,
                tipo_relacionamento=rel.tipo_relacionamento,
                grau_confianca=rel.grau_confianca,
                origem="gemini",
                aprovado=True,
                nome_tabela_origem=rel.tabela_origem,
                nome_tabela_destino=rel.tabela_destino,
            ))

        # Atualizar status da sessão
        client.from_("schema_analysis_sessions").update({
            "status": "analisado",
        }).eq("id", session_id).execute()

        # Audit log — sem payload Gemini (apenas metadados)
        _registrar_audit(
            client, user_id, "inferir_schema_gemini",
            "schema_analysis_sessions", session_id,
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
        return bool(settings.GEMINI_API_KEY)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Use Case 3: Obter sessão completa
# ---------------------------------------------------------------------------

class GetSessaoUseCase:
    async def execute(self, user_id: str, session_id: str) -> GetSessaoResponse:
        client = get_supabase_service_client()
        if client is None:
            return GetSessaoResponse(ok=False, error="Supabase service_role não configurado.")

        # Validar posse
        sess_res = (
            client.from_("schema_analysis_sessions")
            .select("id, status, total_arquivos")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        sess = getattr(sess_res, "data", None)
        if not sess:
            return GetSessaoResponse(ok=False, error="Sessão não encontrada ou acesso negado.")

        tabs_res = (
            client.from_("schema_analysis_tables")
            .select("id, nome_arquivo, nome_tabela_sugerido, colunas_schema, total_linhas")
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        tabs_data = getattr(tabs_res, "data", []) or []

        tabelas = []
        id_to_nome: dict[str, str] = {}
        for tab in tabs_data:
            id_to_nome[tab["id"]] = tab["nome_tabela_sugerido"]
            colunas_raw = tab.get("colunas_schema", [])
            tabelas.append(TabelaUploadedDTO(
                table_id=tab["id"],
                nome_arquivo=tab["nome_arquivo"],
                nome_tabela_sugerido=tab["nome_tabela_sugerido"],
                total_linhas=tab.get("total_linhas", 0),
                colunas=[ColunaSchemaDTO(**c) for c in colunas_raw],
            ))

        rels_res = (
            client.from_("schema_analysis_relationships")
            .select("id, tabela_origem_id, coluna_origem, tabela_destino_id, coluna_destino, tipo_relacionamento, grau_confianca, origem, aprovado")
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        rels_data = getattr(rels_res, "data", []) or []

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
                aprovado=r.get("aprovado", True),
                nome_tabela_origem=id_to_nome.get(r["tabela_origem_id"], ""),
                nome_tabela_destino=id_to_nome.get(r["tabela_destino_id"], ""),
            )
            for r in rels_data
        ]

        return GetSessaoResponse(
            ok=True,
            session_id=session_id,
            status=sess.get("status", ""),
            total_arquivos=sess.get("total_arquivos", 0),
            tabelas=tabelas,
            relacionamentos=relacionamentos,
        )


# ---------------------------------------------------------------------------
# Use Case 4: Editar tipo de coluna
# ---------------------------------------------------------------------------

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

        client = get_supabase_service_client()
        if client is None:
            return EditarColunaResponse(ok=False, error="Supabase service_role não configurado.")

        # Validar posse: tabela deve pertencer ao user_id E à sessão
        tab_res = (
            client.from_("schema_analysis_tables")
            .select("id, colunas_schema")
            .eq("id", table_id)
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        tab = getattr(tab_res, "data", None)
        if not tab:
            return EditarColunaResponse(ok=False, error="Tabela não encontrada ou acesso negado.")

        colunas: list[dict] = tab.get("colunas_schema", [])
        col_found = False
        for c in colunas:
            if c["nome"] == column_name:
                c["tipo_sugerido"] = novo_tipo
                c["editado_pelo_usuario"] = True
                col_found = True
                break

        if not col_found:
            return EditarColunaResponse(ok=False, error=f"Coluna '{column_name}' não encontrada.")

        client.from_("schema_analysis_tables").update({
            "colunas_schema": colunas,
        }).eq("id", table_id).execute()

        _registrar_audit(
            client, user_id, "editar_tipo_coluna",
            "schema_analysis_tables", table_id,
            f"Coluna '{column_name}' → '{novo_tipo}'",
        )

        return EditarColunaResponse(ok=True)


# ---------------------------------------------------------------------------
# Use Case 5: Criar relacionamento manual
# ---------------------------------------------------------------------------

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

        client = get_supabase_service_client()
        if client is None:
            return CriarRelacionamentoResponse(ok=False, error="Supabase service_role não configurado.")

        # Validar que ambas as tabelas pertencem ao user_id E à sessão
        for tid in (tabela_origem_id, tabela_destino_id):
            check = (
                client.from_("schema_analysis_tables")
                .select("id")
                .eq("id", tid)
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if not getattr(check, "data", None):
                return CriarRelacionamentoResponse(ok=False, error=f"Tabela {tid} não encontrada ou acesso negado.")

        rel_res = (
            client.from_("schema_analysis_relationships")
            .insert([{
                "session_id": session_id,
                "user_id": user_id,
                "tabela_origem_id": tabela_origem_id,
                "coluna_origem": coluna_origem,
                "tabela_destino_id": tabela_destino_id,
                "coluna_destino": coluna_destino,
                "tipo_relacionamento": tipo_relacionamento,
                "grau_confianca": 1.0,
                "origem": "usuario",
                "aprovado": True,
            }])
            .select("id")
            .execute()
        )
        rel_data = getattr(rel_res, "data", None)
        if not rel_data:
            return CriarRelacionamentoResponse(ok=False, error="Falha ao criar relacionamento.")

        rel_id = rel_data[0]["id"]
        _registrar_audit(client, user_id, "criar_relacionamento_manual", "schema_analysis_relationships", rel_id)

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


# ---------------------------------------------------------------------------
# Use Case 6: Editar relacionamento
# ---------------------------------------------------------------------------

class EditarRelacionamentoUseCase:
    async def execute(
        self,
        user_id: str,
        session_id: str,
        relationship_id: str,
        aprovado: bool | None,
        tipo_relacionamento: str | None,
    ) -> EditarRelacionamentoResponse:
        client = get_supabase_service_client()
        if client is None:
            return EditarRelacionamentoResponse(ok=False, error="Supabase service_role não configurado.")

        # Validar posse
        check = (
            client.from_("schema_analysis_relationships")
            .select("id")
            .eq("id", relationship_id)
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if not getattr(check, "data", None):
            return EditarRelacionamentoResponse(ok=False, error="Relacionamento não encontrado ou acesso negado.")

        updates: dict = {}
        if aprovado is not None:
            updates["aprovado"] = aprovado
        if tipo_relacionamento is not None:
            if tipo_relacionamento not in ("1:1", "1:N", "N:N"):
                return EditarRelacionamentoResponse(ok=False, error="Tipo de relacionamento inválido.")
            updates["tipo_relacionamento"] = tipo_relacionamento

        if updates:
            client.from_("schema_analysis_relationships").update(updates).eq("id", relationship_id).execute()

        _registrar_audit(client, user_id, "editar_relacionamento", "schema_analysis_relationships", relationship_id)
        return EditarRelacionamentoResponse(ok=True)


# ---------------------------------------------------------------------------
# Use Case 7: Commit — gerar DDL e executar no Supabase
# ---------------------------------------------------------------------------

def _gerar_sql_create_table(nome_tabela: str, colunas: list[dict], com_pk: bool) -> str:
    linhas = []
    if com_pk:
        linhas.append("  id UUID PRIMARY KEY DEFAULT gen_random_uuid()")

    for col in colunas:
        nome = col["nome"]
        # Evita coluna 'id' duplicada quando PK é auto-adicionada
        if com_pk and nome.lower() == "id":
            continue
        if not _validar_identifier(nome):
            nome = f'"{nome}"'
        tipo = col.get("tipo_sugerido") or col.get("tipo_bruto", "TEXT")
        if not _validar_tipo_postgres(tipo):
            tipo = "TEXT"
        nulo = "" if col.get("nulo_permitido", True) else " NOT NULL"
        linhas.append(f"  {nome} {tipo}{nulo}")

    cols_sql = ",\n".join(linhas)
    return f'CREATE TABLE IF NOT EXISTS "{nome_tabela}" (\n{cols_sql}\n);'


def _gerar_sql_fk(
    tabela_origem: str,
    coluna_origem: str,
    tabela_destino: str,
    coluna_destino: str,
) -> str:
    constraint_name = f"fk_{tabela_origem}_{coluna_origem}_{tabela_destino}"[:62]
    return (
        f'ALTER TABLE "{tabela_origem}" ADD CONSTRAINT "{constraint_name}" '
        f'FOREIGN KEY ("{coluna_origem}") REFERENCES "{tabela_destino}" ("{coluna_destino}");'
    )


class CommitSessaoUseCase:
    async def execute(self, user_id: str, session_id: str) -> CommitSessaoResponse:
        client = get_supabase_service_client()
        if client is None:
            return CommitSessaoResponse(ok=False, error="Supabase service_role não configurado.")

        # Validar posse da sessão
        sess_res = (
            client.from_("schema_analysis_sessions")
            .select("id, total_arquivos, status")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        sess = getattr(sess_res, "data", None)
        if not sess:
            return CommitSessaoResponse(ok=False, error="Sessão não encontrada ou acesso negado.")

        if sess.get("status") == "confirmado":
            return CommitSessaoResponse(ok=False, error="Sessão já foi confirmada.")

        total_arquivos = sess.get("total_arquivos", 0)
        com_pk_fk = total_arquivos > 1

        # Buscar tabelas e relacionamentos aprovados
        tabs_res = (
            client.from_("schema_analysis_tables")
            .select("id, nome_arquivo, nome_tabela_sugerido, colunas_schema, total_linhas")
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        tabs_data = getattr(tabs_res, "data", []) or []

        rels_res = (
            client.from_("schema_analysis_relationships")
            .select("id, tabela_origem_id, coluna_origem, tabela_destino_id, coluna_destino, tipo_relacionamento")
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .eq("aprovado", True)
            .execute()
        )
        rels_data = getattr(rels_res, "data", []) or []

        id_to_nome: dict[str, str] = {t["id"]: t["nome_tabela_sugerido"] for t in tabs_data}

        # Gerar SQL
        sql_parts: list[str] = [
            "-- DamaBox: DDL gerado automaticamente",
            f"-- Sessão: {session_id}",
            "",
        ]
        tabelas_criadas: list[str] = []

        for tab in tabs_data:
            nome_tabela = tab["nome_tabela_sugerido"]
            if not _validar_identifier(nome_tabela):
                return CommitSessaoResponse(ok=False, error=f"Nome de tabela inválido: {nome_tabela}")

            colunas = tab.get("colunas_schema", [])
            sql_parts.append(_gerar_sql_create_table(nome_tabela, colunas, com_pk_fk))
            sql_parts.append("")
            tabelas_criadas.append(nome_tabela)

        if com_pk_fk:
            for rel in rels_data:
                origem_nome = id_to_nome.get(rel["tabela_origem_id"])
                destino_nome = id_to_nome.get(rel["tabela_destino_id"])
                if origem_nome and destino_nome:
                    sql_parts.append(_gerar_sql_fk(
                        origem_nome,
                        rel["coluna_origem"],
                        destino_nome,
                        rel["coluna_destino"],
                    ))
                    sql_parts.append("")

        sql_final = "\n".join(sql_parts)

        # Registrar metadados em user_tables + user_table_columns
        user_tables_criadas: list[str] = []
        try:
            for tab in tabs_data:
                nome_tabela = tab["nome_tabela_sugerido"]

                # Verificar se nome_tabela é único para o usuário
                existente = (
                    client.from_("user_tables")
                    .select("id")
                    .eq("user_id", user_id)
                    .eq("nome_tabela", nome_tabela)
                    .maybe_single()
                    .execute()
                )
                if getattr(existente, "data", None):
                    return CommitSessaoResponse(
                        ok=False,
                        sql_gerado=sql_final,
                        error=f"Tabela '{nome_tabela}' já existe para este usuário.",
                    )

                ext = tab["nome_arquivo"].rsplit(".", 1)[-1].lower() if "." in tab["nome_arquivo"] else "csv"
                ut_res = (
                    client.from_("user_tables")
                    .insert([{
                        "user_id": user_id,
                        "nome_tabela": nome_tabela,
                        "nome_origem_arquivo": tab["nome_arquivo"],
                        "tipo_arquivo": ext,
                        "total_linhas": tab.get("total_linhas", 0),
                    }])
                    .select("id")
                    .execute()
                )
                ut_data = getattr(ut_res, "data", None)
                if not ut_data:
                    return CommitSessaoResponse(ok=False, sql_gerado=sql_final, error="Falha ao registrar tabela em user_tables.")

                ut_id = ut_data[0]["id"]
                user_tables_criadas.append(ut_id)

                # Inserir colunas em user_table_columns
                colunas = tab.get("colunas_schema", [])
                for idx, col in enumerate(colunas):
                    nome_col = col["nome"]
                    if not _validar_identifier(nome_col):
                        continue
                    tipo = col.get("tipo_sugerido") or "TEXT"
                    if not _validar_tipo_postgres(tipo):
                        tipo = "TEXT"

                    client.from_("user_table_columns").insert([{
                        "user_table_id": ut_id,
                        "nome_coluna": nome_col,
                        "tipo_dado": tipo.split("(")[0],  # VARCHAR sem tamanho
                        "permite_nulo": col.get("nulo_permitido", True),
                        "chave_primaria": (nome_col == "id" and com_pk_fk),
                        "indice": idx,
                    }]).execute()

            # Relacionamentos em user_table_relationships
            if com_pk_fk:
                # Precisamos dos IDs de user_tables pelo nome
                nome_to_ut_id: dict[str, str] = {}
                for ut_id in user_tables_criadas:
                    ut_check = (
                        client.from_("user_tables")
                        .select("id, nome_tabela")
                        .eq("id", ut_id)
                        .maybe_single()
                        .execute()
                    )
                    ut_d = getattr(ut_check, "data", None)
                    if ut_d:
                        nome_to_ut_id[ut_d["nome_tabela"]] = ut_d["id"]

                for rel in rels_data:
                    origem_nome = id_to_nome.get(rel["tabela_origem_id"])
                    destino_nome = id_to_nome.get(rel["tabela_destino_id"])
                    origem_ut = nome_to_ut_id.get(origem_nome or "")
                    destino_ut = nome_to_ut_id.get(destino_nome or "")
                    if not origem_ut or not destino_ut:
                        continue

                    # Buscar IDs das colunas
                    col_origem_res = (
                        client.from_("user_table_columns")
                        .select("id")
                        .eq("user_table_id", origem_ut)
                        .eq("nome_coluna", rel["coluna_origem"])
                        .maybe_single()
                        .execute()
                    )
                    col_destino_res = (
                        client.from_("user_table_columns")
                        .select("id")
                        .eq("user_table_id", destino_ut)
                        .eq("nome_coluna", rel["coluna_destino"])
                        .maybe_single()
                        .execute()
                    )
                    col_origem_d = getattr(col_origem_res, "data", None)
                    col_destino_d = getattr(col_destino_res, "data", None)
                    if col_origem_d and col_destino_d:
                        client.from_("user_table_relationships").insert([{
                            "user_id": user_id,
                            "tabela_origem_id": origem_ut,
                            "coluna_origem_id": col_origem_d["id"],
                            "tabela_destino_id": destino_ut,
                            "coluna_destino_id": col_destino_d["id"],
                            "tipo_relacionamento": rel.get("tipo_relacionamento", "1:N"),
                        }]).execute()

        except Exception as exc:
            logger.exception("CommitSessaoUseCase erro ao registrar metadados: %s", exc)
            return CommitSessaoResponse(ok=False, sql_gerado=sql_final, error=str(exc))

        # Marcar sessão como confirmada e limpar staging
        client.from_("schema_analysis_sessions").update({"status": "confirmado"}).eq("id", session_id).execute()
        client.from_("schema_analysis_tables").delete().eq("session_id", session_id).execute()
        client.from_("schema_analysis_relationships").delete().eq("session_id", session_id).execute()

        _registrar_audit(
            client, user_id, "commit_schema",
            "schema_analysis_sessions", session_id,
            f"Commit realizado: {len(tabelas_criadas)} tabela(s) criadas",
        )

        return CommitSessaoResponse(
            ok=True,
            sql_gerado=sql_final,
            tabelas_criadas=tabelas_criadas,
        )
