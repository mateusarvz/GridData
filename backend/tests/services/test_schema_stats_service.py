import pandas as pd

from app.services.schema_stats_service import compute_table_stats, infer_postgres_type, normalize_for_postgres


def test_infer_postgres_type_prefers_date_for_date_strings():
    series = pd.Series(["2026-07-31", "2026-08-01", "2026-08-02"])

    assert infer_postgres_type(series) == "DATE"


def test_infer_postgres_type_prefers_int_for_integer_values():
    series = pd.Series(["1", "2", "300"])

    assert infer_postgres_type(series) == "INT"


def test_infer_postgres_type_prefers_decimal_for_decimal_values():
    series = pd.Series(["10.5", "20,75", "3.1415"])

    assert infer_postgres_type(series) == "DECIMAL(18,6)"


def test_infer_postgres_type_falls_back_to_text():
    series = pd.Series(["abc", "def", "ghi"])

    assert infer_postgres_type(series) == "VARCHAR(255)"


def test_infer_postgres_type_detects_uuid():
    series = pd.Series([
        "550e8400-e29b-41d4-a716-446655440000",
        "550e8400-e29b-41d4-a716-446655440001",
    ])

    assert infer_postgres_type(series) == "UUID"


def test_infer_postgres_type_detects_timestamp():
    series = pd.Series([
        "2026-07-31 10:15:00",
        "2026-07-31T11:20:00Z",
    ])

    assert infer_postgres_type(series) == "TIMESTAMP WITH TIME ZONE"


def test_infer_postgres_type_does_not_treat_month_name_as_date():
    series = pd.Series(["November", "December", "January"])

    assert infer_postgres_type(series) == "VARCHAR(255)"


def test_normalize_for_postgres_decimal_pt_br_and_en():
    assert normalize_for_postgres("10,5") == 10.5
    assert normalize_for_postgres("10.5") == 10.5


def test_compute_table_stats_populates_tipo_sugerido():
    df = pd.DataFrame(
        {
            "data": ["2026-07-31", "2026-08-01"],
            "quantidade": ["1", "2"],
            "valor": ["10.5", "20.0"],
            "descricao": ["alpha", "beta"],
        }
    )

    stats = compute_table_stats(df)
    inferred = {col["nome"]: col["tipo_sugerido"] for col in stats}

    assert inferred["data"] == "DATE"
    assert inferred["quantidade"] == "INT"
    assert inferred["valor"] == "DECIMAL(18,6)"
    assert inferred["descricao"] == "VARCHAR(255)"
