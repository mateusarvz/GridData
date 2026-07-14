"""
Testes do módulo schema_analysis.

Cobre:
- Arquivo único → sem PK/FK, sem relacionamentos
- Múltiplos arquivos → relacionamentos presentes
- Isolamento por user_id (acesso 403 cruzado)
- Geração de SQL coerente no commit
"""

import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers de mock do Supabase client
# ---------------------------------------------------------------------------

def _make_supabase_mock(session_data=None, tables_data=None, rels_data=None):
    """Cria um mock do cliente Supabase service_role."""
    client = MagicMock()

    def _chain(data):
        """Retorna uma cadeia de mocks que termina com .execute() retornando data."""
        resp = MagicMock()
        resp.data = data

        chain = MagicMock()
        chain.execute = MagicMock(return_value=resp)
        chain.select = MagicMock(return_value=chain)
        chain.insert = MagicMock(return_value=chain)
        chain.update = MagicMock(return_value=chain)
        chain.delete = MagicMock(return_value=chain)
        chain.eq = MagicMock(return_value=chain)
        chain.maybe_single = MagicMock(return_value=chain)
        chain.order = MagicMock(return_value=chain)
        return chain

    client.from_ = MagicMock(side_effect=lambda table: {
        "schema_analysis_sessions": _chain(session_data),
        "schema_analysis_tables": _chain(tables_data),
        "schema_analysis_relationships": _chain(rels_data or []),
        "audit_logs": _chain([]),
        "user_tables": _chain([]),
        "user_table_columns": _chain([]),
        "user_table_relationships": _chain([]),
    }.get(table, _chain([])))

    return client


# ---------------------------------------------------------------------------
# Use Case: CriarSessaoUseCase
# ---------------------------------------------------------------------------

class TestCriarSessaoUseCase:
    @pytest.mark.asyncio
    async def test_cria_sessao_arquivo_unico(self):
        from app.modules.schema_analysis.application.use_cases import CriarSessaoUseCase

        # CSV simples em bytes
        csv_content = b"id,nome,valor\n1,Alice,100.0\n2,Bob,200.5\n"

        session_mock_data = [{"id": "sess-001"}]
        table_mock_data = [{"id": "tab-001"}]

        with patch(
            "app.modules.schema_analysis.application.use_cases.get_supabase_service_client",
            return_value=_make_supabase_mock(session_mock_data, table_mock_data),
        ):
            use_case = CriarSessaoUseCase()
            result = await use_case.execute("user-A", [("vendas.csv", csv_content)])

        assert result.ok is True
        assert result.session_id == "sess-001"
        assert len(result.tabelas) == 1
        assert result.tabelas[0].nome_arquivo == "vendas.csv"
        assert result.tabelas[0].total_linhas == 2
        # Deve ter 3 colunas
        assert len(result.tabelas[0].colunas) == 3
        col_nomes = [c.nome for c in result.tabelas[0].colunas]
        assert "id" in col_nomes
        assert "nome" in col_nomes
        assert "valor" in col_nomes


# ---------------------------------------------------------------------------
# Use Case: InferirSchemaUseCase — arquivo único sem relacionamentos
# ---------------------------------------------------------------------------

class TestInferirSchemaUseCase:
    @pytest.mark.asyncio
    async def test_arquivo_unico_sem_relacionamentos(self):
        from app.modules.schema_analysis.application.use_cases import InferirSchemaUseCase
        from app.services.gemini_schema_service import SchemaSuggestion, ColumnSuggestion

        sess_data = {"id": "sess-001", "total_arquivos": 1, "status": "aguardando_analise"}
        tabs_data = [
            {
                "id": "tab-001",
                "nome_arquivo": "vendas.csv",
                "nome_tabela_sugerido": "vendas",
                "colunas_schema": [
                    {"nome": "id", "tipo_bruto": "int64", "tipo_sugerido": "", "nulo_permitido": False, "editado_pelo_usuario": False},
                    {"nome": "valor", "tipo_bruto": "float64", "tipo_sugerido": "", "nulo_permitido": True, "editado_pelo_usuario": False},
                ],
                "total_linhas": 100,
            }
        ]

        mock_sugestao = SchemaSuggestion(
            tabelas={
                "vendas": [
                    ColumnSuggestion(nome="id", tipo_sugerido="BIGINT"),
                    ColumnSuggestion(nome="valor", tipo_sugerido="DECIMAL(10,2)"),
                ]
            },
            relacionamentos=[],  # Gemini retorna vazio para 1 arquivo
        )

        with (
            patch(
                "app.modules.schema_analysis.application.use_cases.get_supabase_service_client",
                return_value=_make_supabase_mock(sess_data, tabs_data),
            ),
            patch(
                "app.modules.schema_analysis.application.use_cases.suggest_schema",
                new=AsyncMock(return_value=mock_sugestao),
            ),
        ):
            use_case = InferirSchemaUseCase()
            result = await use_case.execute("user-A", "sess-001")

        assert result.ok is True
        # Arquivo único → sem relacionamentos
        assert len(result.relacionamentos) == 0

        # Tipos sugeridos devem estar presentes
        col_tipos = {c.nome: c.tipo_sugerido for t in result.tabelas for c in t.colunas}
        assert col_tipos["id"] == "BIGINT"
        assert col_tipos["valor"] == "DECIMAL(10,2)"

    @pytest.mark.asyncio
    async def test_multiplos_arquivos_com_relacionamentos(self):
        from app.modules.schema_analysis.application.use_cases import InferirSchemaUseCase
        from app.services.gemini_schema_service import (
            SchemaSuggestion,
            ColumnSuggestion,
            RelationshipSuggestion,
        )

        sess_data = {"id": "sess-002", "total_arquivos": 2, "status": "aguardando_analise"}
        tabs_data = [
            {
                "id": "tab-A",
                "nome_arquivo": "clientes.csv",
                "nome_tabela_sugerido": "clientes",
                "colunas_schema": [
                    {"nome": "id", "tipo_bruto": "int64", "tipo_sugerido": "", "nulo_permitido": False, "editado_pelo_usuario": False},
                ],
                "total_linhas": 50,
            },
            {
                "id": "tab-B",
                "nome_arquivo": "pedidos.csv",
                "nome_tabela_sugerido": "pedidos",
                "colunas_schema": [
                    {"nome": "id", "tipo_bruto": "int64", "tipo_sugerido": "", "nulo_permitido": False, "editado_pelo_usuario": False},
                    {"nome": "cliente_id", "tipo_bruto": "int64", "tipo_sugerido": "", "nulo_permitido": True, "editado_pelo_usuario": False},
                ],
                "total_linhas": 200,
            },
        ]

        mock_sugestao = SchemaSuggestion(
            tabelas={
                "clientes": [ColumnSuggestion(nome="id", tipo_sugerido="BIGINT")],
                "pedidos": [
                    ColumnSuggestion(nome="id", tipo_sugerido="BIGINT"),
                    ColumnSuggestion(nome="cliente_id", tipo_sugerido="BIGINT"),
                ],
            },
            relacionamentos=[
                RelationshipSuggestion(
                    tabela_origem="pedidos",
                    coluna_origem="cliente_id",
                    tabela_destino="clientes",
                    coluna_destino="id",
                    tipo_relacionamento="1:N",
                    grau_confianca=0.95,
                )
            ],
        )

        rel_insert_data = [{"id": "rel-001"}]

        with (
            patch(
                "app.modules.schema_analysis.application.use_cases.get_supabase_service_client",
                return_value=_make_supabase_mock(sess_data, tabs_data, rel_insert_data),
            ),
            patch(
                "app.modules.schema_analysis.application.use_cases.suggest_schema",
                new=AsyncMock(return_value=mock_sugestao),
            ),
        ):
            use_case = InferirSchemaUseCase()
            result = await use_case.execute("user-A", "sess-002")

        assert result.ok is True
        # Múltiplos arquivos → relacionamentos sugeridos
        assert len(result.relacionamentos) >= 1
        rel = result.relacionamentos[0]
        assert rel.coluna_origem == "cliente_id"
        assert rel.tipo_relacionamento == "1:N"


# ---------------------------------------------------------------------------
# Isolamento por user_id — acesso cruzado deve negar
# ---------------------------------------------------------------------------

class TestIsolamentoUserid:
    @pytest.mark.asyncio
    async def test_user_b_nao_acessa_sessao_de_user_a(self):
        from app.modules.schema_analysis.application.use_cases import GetSessaoUseCase

        # Supabase retorna None para user_id errado (simula RLS + validação explícita)
        client = MagicMock()
        resp = MagicMock()
        resp.data = None  # Sessão não encontrada para user-B
        chain = MagicMock()
        chain.execute = MagicMock(return_value=resp)
        chain.select = MagicMock(return_value=chain)
        chain.eq = MagicMock(return_value=chain)
        chain.maybe_single = MagicMock(return_value=chain)
        client.from_ = MagicMock(return_value=chain)

        with patch(
            "app.modules.schema_analysis.application.use_cases.get_supabase_service_client",
            return_value=client,
        ):
            use_case = GetSessaoUseCase()
            # user-B tenta acessar sessão de user-A
            result = await use_case.execute("user-B", "sess-de-user-A")

        assert result.ok is False
        assert "acesso negado" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_user_b_nao_edita_coluna_de_user_a(self):
        from app.modules.schema_analysis.application.use_cases import EditarColunaUseCase

        client = MagicMock()
        resp = MagicMock()
        resp.data = None
        chain = MagicMock()
        chain.execute = MagicMock(return_value=resp)
        chain.select = MagicMock(return_value=chain)
        chain.eq = MagicMock(return_value=chain)
        chain.maybe_single = MagicMock(return_value=chain)
        client.from_ = MagicMock(return_value=chain)

        with patch(
            "app.modules.schema_analysis.application.use_cases.get_supabase_service_client",
            return_value=client,
        ):
            use_case = EditarColunaUseCase()
            result = await use_case.execute("user-B", "sess-A", "tab-A", "nome", "TEXT")

        assert result.ok is False
        assert "acesso negado" in (result.error or "").lower()


# ---------------------------------------------------------------------------
# CommitSessaoUseCase — SQL gerado
# ---------------------------------------------------------------------------

class TestCommitSessaoUseCase:
    def _make_commit_client(self, sess_data, tabs_data, rels_data=None):
        """Mock mais granular: retorna dados corretos por tabela Supabase."""
        from unittest.mock import MagicMock

        def make_chain(data):
            resp = MagicMock()
            resp.data = data
            chain = MagicMock()
            chain.execute = MagicMock(return_value=resp)
            chain.select = MagicMock(return_value=chain)
            chain.insert = MagicMock(return_value=chain)
            chain.update = MagicMock(return_value=chain)
            chain.delete = MagicMock(return_value=chain)
            chain.eq = MagicMock(return_value=chain)
            chain.maybe_single = MagicMock(return_value=chain)
            chain.order = MagicMock(return_value=chain)
            return chain

        call_counts = {"user_tables_insert": 0, "user_table_columns_insert": 0}

        def from_side_effect(table):
            if table == "schema_analysis_sessions":
                return make_chain(sess_data)
            if table == "schema_analysis_tables":
                return make_chain(tabs_data)
            if table == "schema_analysis_relationships":
                return make_chain(rels_data or [])
            if table == "user_tables":
                # Verificar existência retorna None; insert retorna novo id
                chain = MagicMock()
                resp_none = MagicMock(); resp_none.data = None
                resp_insert = MagicMock(); resp_insert.data = [{"id": f"ut-{call_counts['user_tables_insert']}"}]
                call_counts["user_tables_insert"] += 1
                chain.select = MagicMock(return_value=make_chain(None))
                chain.insert = MagicMock(return_value=make_chain([{"id": f"ut-{call_counts['user_tables_insert']}"}]))
                chain.update = MagicMock(return_value=make_chain(None))
                chain.eq = MagicMock(return_value=chain)
                chain.execute = MagicMock(return_value=resp_none)
                chain.maybe_single = MagicMock(return_value=make_chain(None))
                return chain
            if table == "user_table_columns":
                return make_chain([{"id": f"col-{call_counts['user_table_columns_insert']}"}])
            if table == "user_table_relationships":
                return make_chain([])
            if table == "audit_logs":
                return make_chain([])
            return make_chain([])

        client = MagicMock()
        client.from_ = MagicMock(side_effect=from_side_effect)
        return client

    @pytest.mark.asyncio
    async def test_sql_gerado_arquivo_unico_sem_pk(self):
        from app.modules.schema_analysis.application.use_cases import CommitSessaoUseCase

        sess_data = {"id": "sess-001", "total_arquivos": 1, "status": "analisado"}
        tabs_data = [
            {
                "id": "tab-001",
                "nome_arquivo": "produtos.csv",
                "nome_tabela_sugerido": "produtos",
                "colunas_schema": [
                    {"nome": "nome", "tipo_bruto": "object", "tipo_sugerido": "VARCHAR(255)", "nulo_permitido": True, "editado_pelo_usuario": False},
                    {"nome": "preco", "tipo_bruto": "float64", "tipo_sugerido": "DECIMAL(10,2)", "nulo_permitido": True, "editado_pelo_usuario": False},
                ],
                "total_linhas": 10,
            }
        ]

        client = self._make_commit_client(sess_data, tabs_data)

        with patch(
            "app.modules.schema_analysis.application.use_cases.get_supabase_service_client",
            return_value=client,
        ):
            use_case = CommitSessaoUseCase()
            result = await use_case.execute("user-A", "sess-001")

        sql = result.sql_gerado
        # Arquivo único → sem "id UUID PRIMARY KEY"
        assert "id UUID PRIMARY KEY" not in sql
        # Deve conter CREATE TABLE
        assert "CREATE TABLE" in sql
        assert "produtos" in sql
        assert "VARCHAR(255)" in sql
        assert "DECIMAL(10,2)" in sql
        # Sem FOREIGN KEY para arquivo único
        assert "FOREIGN KEY" not in sql

    @pytest.mark.asyncio
    async def test_sql_gerado_multiplos_arquivos_com_fk(self):
        from app.modules.schema_analysis.application.use_cases import CommitSessaoUseCase

        sess_data = {"id": "sess-002", "total_arquivos": 2, "status": "analisado"}
        tabs_data = [
            {
                "id": "tab-A",
                "nome_arquivo": "clientes.csv",
                "nome_tabela_sugerido": "clientes",
                "colunas_schema": [
                    {"nome": "id", "tipo_bruto": "int64", "tipo_sugerido": "BIGINT", "nulo_permitido": False, "editado_pelo_usuario": False},
                ],
                "total_linhas": 5,
            },
            {
                "id": "tab-B",
                "nome_arquivo": "pedidos.csv",
                "nome_tabela_sugerido": "pedidos",
                "colunas_schema": [
                    {"nome": "id", "tipo_bruto": "int64", "tipo_sugerido": "BIGINT", "nulo_permitido": False, "editado_pelo_usuario": False},
                    {"nome": "cliente_id", "tipo_bruto": "int64", "tipo_sugerido": "BIGINT", "nulo_permitido": True, "editado_pelo_usuario": False},
                ],
                "total_linhas": 20,
            },
        ]
        rels_data = [
            {
                "id": "rel-001",
                "tabela_origem_id": "tab-B",
                "coluna_origem": "cliente_id",
                "tabela_destino_id": "tab-A",
                "coluna_destino": "id",
                "tipo_relacionamento": "1:N",
            }
        ]

        client = self._make_commit_client(sess_data, tabs_data, rels_data)

        with patch(
            "app.modules.schema_analysis.application.use_cases.get_supabase_service_client",
            return_value=client,
        ):
            use_case = CommitSessaoUseCase()
            result = await use_case.execute("user-A", "sess-002")

        sql = result.sql_gerado
        # Múltiplos arquivos → deve ter PK
        assert "id UUID PRIMARY KEY" in sql
        # Deve ter FK
        assert "FOREIGN KEY" in sql
        assert "cliente_id" in sql
        # Coluna 'id' não duplicada
        assert sql.count("id UUID PRIMARY KEY") == sql.count("CREATE TABLE")




# ---------------------------------------------------------------------------
# gemini_schema_service — fallback e mascaramento de colunas sensíveis
# ---------------------------------------------------------------------------

class TestGeminiSchemaService:
    def test_coluna_sensivel_sem_exemplos(self):
        from app.services.gemini_schema_service import _is_sensitive
        assert _is_sensitive("cpf") is True
        assert _is_sensitive("senha_usuario") is True
        assert _is_sensitive("email") is True
        assert _is_sensitive("telefone") is True
        assert _is_sensitive("nome_produto") is False
        assert _is_sensitive("preco") is False

    @pytest.mark.asyncio
    async def test_fallback_quando_gemini_indisponivel(self):
        from app.services.gemini_schema_service import suggest_schema, TableSchemaInput, ColumnInput

        tables = [
            TableSchemaInput(
                nome_tabela="vendas",
                nome_arquivo="vendas.csv",
                table_id="tab-001",
                colunas=[
                    ColumnInput(nome="valor", tipo_bruto="float64"),
                    ColumnInput(nome="data", tipo_bruto="datetime64[ns]"),
                ],
            )
        ]

        with patch("app.services.gemini_schema_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""  # Sem chave → fallback
            result = await suggest_schema(tables, infer_relationships=False)

        assert result.relacionamentos == []
        tipos = {s.nome: s.tipo_sugerido for s in result.tabelas["vendas"]}
        assert tipos["valor"] == "DOUBLE PRECISION"
        assert tipos["data"] == "TIMESTAMP WITH TIME ZONE"
