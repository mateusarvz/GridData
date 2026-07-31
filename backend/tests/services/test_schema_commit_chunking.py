import pytest

from app.modules.schema_analysis.application.use_cases import _build_commit_sql


def test_build_commit_sql_chunks_large_row_sets():
    tabs_data = [
        {
            "id": "tab-1",
            "nome_arquivo": "energy.csv",
            "nome_tabela_sugerido": "energy_production_dataset_arvz",
            "total_linhas": 205,
            "colunas_schema": [
                {"nome": "Date", "tipo_sugerido": "DATE", "nulo_permitido": True, "tipo_bruto": "object"},
                {"nome": "Production", "tipo_sugerido": "INT", "nulo_permitido": True, "tipo_bruto": "int64"},
            ],
        }
    ]
    rows_by_table = {
        "tab-1": [{"Date": "11/30/2025", "Production": i} for i in range(205)]
    }

    sql, tables = _build_commit_sql("user-1", "sess-1", tabs_data, [], rows_by_table)

    assert tables == ["energy_production_dataset_arvz"]
    assert sql.count("INSERT INTO table_schema.\"energy_production_dataset_arvz\"") == 3
