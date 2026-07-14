import json
from typing import Any

from app.core.config import settings
import redis.asyncio as redis


class RedisDataSessionStore:
    _memory_store: dict[str, dict[str, str]] = {}

    def __init__(self) -> None:
        self.client = None
        try:
            self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            self.client = None

    async def _get_client(self):
        if self.client is None:
            return None
        return self.client

    async def save_table(self, user_id: str, table_id: str, metadata: dict[str, Any], preview: list[dict[str, Any]], ttl_seconds: int) -> None:
        key = f"data_session:{user_id}"
        payload = {
            "metadata": metadata,
            "preview": preview,
        }
        client = await self._get_client()
        if client is not None:
            try:
                await client.hset(key, table_id, json.dumps(payload, default=str))
                await client.expire(key, ttl_seconds)
                return
            except Exception:
                pass

        self.__class__._memory_store[key] = self.__class__._memory_store.get(key, {})
        self.__class__._memory_store[key][table_id] = json.dumps(payload, default=str)

    async def list_tables(self, user_id: str) -> list[dict[str, Any]]:
        key = f"data_session:{user_id}"
        client = await self._get_client()
        if client is not None:
            try:
                raw = await client.hgetall(key)
                result: list[dict[str, Any]] = []
                for table_id, value in raw.items():
                    parsed = json.loads(value)
                    metadata = parsed.get("metadata", {})
                    metadata["table_id"] = table_id
                    result.append(metadata)
                return result
            except Exception:
                pass

        raw = self.__class__._memory_store.get(key, {})
        result: list[dict[str, Any]] = []
        for table_id, value in raw.items():
            parsed = json.loads(value)
            metadata = parsed.get("metadata", {})
            metadata["table_id"] = table_id
            result.append(metadata)
        return result

    async def get_table(self, user_id: str, table_id: str) -> dict[str, Any] | None:
        key = f"data_session:{user_id}"
        client = await self._get_client()
        if client is not None:
            try:
                raw = await client.hget(key, table_id)
                if not raw:
                    return None
                parsed = json.loads(raw)
                metadata = parsed.get("metadata", {})
                metadata["table_id"] = table_id
                metadata["preview"] = parsed.get("preview", [])
                return metadata
            except Exception:
                pass

        raw = self.__class__._memory_store.get(key, {}).get(table_id)
        if not raw:
            return None
        parsed = json.loads(raw)
        metadata = parsed.get("metadata", {})
        metadata["table_id"] = table_id
        metadata["preview"] = parsed.get("preview", [])
        return metadata

    async def delete_session(self, user_id: str) -> None:
        key = f"data_session:{user_id}"
        client = await self._get_client()
        if client is not None:
            try:
                await client.delete(key)
                return
            except Exception:
                pass

        self.__class__._memory_store.pop(key, None)
