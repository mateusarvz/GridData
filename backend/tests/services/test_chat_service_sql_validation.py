from DADOS_PARA_LANGCHAIN.services.chat_service import _is_safe_select_sql, _normalize_sql_query


def test_normalize_sql_query_strips_trailing_semicolon_and_fences():
    sql = "```sql\nSELECT * FROM table_schema.users_table;\n```"

    assert _normalize_sql_query(sql) == "SELECT * FROM table_schema.users_table"


def test_is_safe_select_sql_accepts_single_select():
    assert _is_safe_select_sql("SELECT * FROM table_schema.users_table") is True


def test_is_safe_select_sql_rejects_multiple_statements():
    assert _is_safe_select_sql("SELECT * FROM table_schema.users_table; SELECT 1") is False


def test_is_safe_select_sql_rejects_write_statements():
    assert _is_safe_select_sql("INSERT INTO table_schema.users_table VALUES (1)") is False
