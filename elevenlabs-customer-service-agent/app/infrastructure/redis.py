# Caching, session store — async Redis client
import json
from typing import Any

from redis.asyncio import Redis

from app.config import get_settings

_client: Redis | None = None

async def init_redis() -> Redis:
    """Create and store the Redis client. Call once at app startup."""
    global _client
    _client = Redis(
        host=get_settings().redis_host,
        port=get_settings().redis_port,
        decode_responses=True,
        username=get_settings().redis_username,
        password=get_settings().redis_password,
    )
    return _client


def get_redis() -> Redis:
    """Return the current Redis client. Raises if not initialized."""
    if _client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() at startup.")
    return _client


async def close_redis() -> None:
    """Close the Redis connection. Call on app shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# Convenience helpers for session/cache by call SID
def _call_key(call_sid: str, suffix: str = "") -> str:
    return f"call:{call_sid}:{suffix}" if suffix else f"call:{call_sid}"


async def get_call_state(call_sid: str) -> str | None:
    """Get stored state for a call (e.g. JSON string)."""
    redis = get_redis()
    return await redis.get(_call_key(call_sid, "state"))


async def set_call_state(call_sid: str, value: str, ttl_seconds: int | None = 3600) -> None:
    """Set state for a call. Optional TTL (default 1 hour)."""
    redis = get_redis()
    key = _call_key(call_sid, "state")
    await redis.set(key, value, ex=ttl_seconds)


async def delete_call_state(call_sid: str) -> None:
    """Remove state for a call (e.g. on hangup)."""
    redis = get_redis()
    await redis.delete(_call_key(call_sid, "state"))


async def get_json(call_sid: str, subkey: str) -> Any:
    """Get a JSON value for a call (e.g. transcript). Returns decoded object or None."""
    redis = get_redis()
    raw = await redis.get(_call_key(call_sid, subkey))
    return json.loads(raw) if raw else None


async def set_json(call_sid: str, subkey: str, value: Any, ttl_seconds: int | None = 3600) -> None:
    """Set a JSON value for a call."""
    redis = get_redis()
    await redis.set(_call_key(call_sid, subkey), json.dumps(value), ex=ttl_seconds)
