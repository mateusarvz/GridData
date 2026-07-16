from typing import Any


class DataSessionRepository:
    async def save_table(self, user_id: str, table_id: str, metadata: dict[str, Any], preview: list[dict[str, Any]], ttl_seconds: int) -> None:
        raise NotImplementedError

    async def list_tables(self, user_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def get_table(self, user_id: str, table_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    async def delete_session(self, user_id: str) -> None:
        raise NotImplementedError
