import pytest
from unittest.mock import patch, MagicMock


def _make_supabase_mock():
    client = MagicMock()

    resp = MagicMock()
    resp.data = []

    chain = MagicMock()
    chain.execute = MagicMock(return_value=resp)
    chain.insert = MagicMock(return_value=chain)

    client.from_ = MagicMock(return_value=chain)
    client.schema = MagicMock(return_value=client)
    client.rpc = MagicMock(return_value=chain)
    return client


@pytest.mark.asyncio
async def test_criar_sessao_guarda_todas_as_linhas_para_commit():
    from app.modules.schema_analysis.application.use_cases import CriarSessaoUseCase
    import app.modules.schema_analysis.application.use_cases as uc

    csv_content = b"Date,Production\n11/30/2025,100\n12/01/2025,200\n12/02/2025,300\n"

    with patch(
        "app.modules.schema_analysis.application.use_cases.get_supabase_service_client",
        return_value=_make_supabase_mock(),
    ):
        result = await CriarSessaoUseCase().execute("user-a", [("energy.csv", csv_content)])

    assert result.ok is True
    session_id = result.session_id
    assert session_id
    cache = uc._SCHEMA_ANALYSIS_CACHE[session_id]
    rows_by_table = getattr(cache, "rows_by_table", {})
    assert len(rows_by_table[result.tabelas[0].table_id]) == 3
