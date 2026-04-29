import json
from typing import Any, Dict, Optional
from datetime import datetime
from redis.asyncio import Redis
from infrastructure.config.settings import settings


class DateTimeEncoder(json.JSONEncoder):
    """Custom encoder to convert datetime to ISO string"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class RedisSessionCache:
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
        """Save session with datetime support"""
        client = await RedisSessionCache.get_client()
        
        # Convert any datetime to ISO string before saving
        serializable_data = json.loads(
            json.dumps(data, cls=DateTimeEncoder, ensure_ascii=False)
        )
        
        await client.setex(
            f"session:{session_id}",
            ttl_seconds,
            json.dumps(serializable_data, ensure_ascii=False)
        )

    @staticmethod
    async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session and convert ISO strings back to datetime if needed"""
        client = await RedisSessionCache.get_client()
        data = await client.get(f"session:{session_id}")
        if not data:
            return None
        
        return json.loads(data)

    @staticmethod
    async def delete_session(session_id: str):
        client = await RedisSessionCache.get_client()
        await client.delete(f"session:{session_id}")

    @staticmethod
    async def ping():
        client = await RedisSessionCache.get_client()
        return await client.ping()