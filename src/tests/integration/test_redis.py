import pytest
from infrastructure.cache.redis_session import RedisSessionCache

@pytest.mark.integration
async def test_redis_session_cache():
    session_id = "test_session_123"
    test_data = {"patient_id": "pat_001", "risk": "LOW", "turns": 3}

    await RedisSessionCache.set_session(session_id, test_data, ttl_seconds=60)
    retrieved = await RedisSessionCache.get_session(session_id)

    assert retrieved is not None
    assert retrieved["patient_id"] == "pat_001"
    assert retrieved["risk"] == "LOW"

    await RedisSessionCache.delete_session(session_id)
    print("✅ Redis session cache test passed")