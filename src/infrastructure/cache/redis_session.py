import json
from typing import Any, Dict, Optional
from redis.asyncio import Redis
from infrastructure.config.settings import settings

class RedisSessionCache:
    """Redis session cache for conversation turns, risk score, etc."""

    _client: Optional[Redis] = None

    @classmethod
    async def get_client(cls) -> Redis:
        if cls._client is None:
            cls._client = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=5.0
            )
        return cls._client

    @staticmethod
    async def set_session(session_id: str, data: Dict[str, Any], ttl_seconds: int = 3600):
        """Save session data with TTL (default 1 hour)"""
        client = await RedisSessionCache.get_client()
        await client.setex(
            f"session:{session_id}",
            ttl_seconds,
            json.dumps(data, ensure_ascii=False)
        )

    @staticmethod
    async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        client = await RedisSessionCache.get_client()
        data = await client.get(f"session:{session_id}")
        return json.loads(data) if data else None

    @staticmethod
    async def delete_session(session_id: str):
        """Delete session"""
        client = await RedisSessionCache.get_client()
        await client.delete(f"session:{session_id}")

    @staticmethod
    async def ping():
        """Health check for Redis"""
        client = await RedisSessionCache.get_client()
        return await client.ping()