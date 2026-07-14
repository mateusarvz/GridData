import pytest

from app.modules.data_session.infrastructure import redis_data_session_store as store_module


@pytest.mark.asyncio
async def test_falls_back_to_in_memory_store_when_redis_unavailable(monkeypatch):
    def fail_from_url(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(store_module.redis, "from_url", fail_from_url)

    store = store_module.RedisDataSessionStore()
    await store.save_table(
        "user-1",
        "table-1",
        {"file_name": "sample.csv", "columns": ["name"]},
        [{"name": "Alice"}],
        60,
    )

    tables = await store.list_tables("user-1")
    assert len(tables) == 1
    assert tables[0]["file_name"] == "sample.csv"

    table = await store.get_table("user-1", "table-1")
    assert table is not None
    assert table["file_name"] == "sample.csv"

    await store.delete_session("user-1")
    assert await store.list_tables("user-1") == []


@pytest.mark.asyncio
async def test_store_persists_across_instances_when_redis_unavailable(monkeypatch):
    def fail_from_url(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(store_module.redis, "from_url", fail_from_url)

    first_store = store_module.RedisDataSessionStore()
    await first_store.save_table(
        "user-2",
        "table-2",
        {"file_name": "sample.csv", "columns": ["name"]},
        [{"name": "Alice"}],
        60,
    )

    second_store = store_module.RedisDataSessionStore()
    table = await second_store.get_table("user-2", "table-2")

    assert table is not None
    assert table["file_name"] == "sample.csv"
