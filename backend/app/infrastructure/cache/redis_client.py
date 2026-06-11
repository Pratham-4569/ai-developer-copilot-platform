"""Async Redis client factory and tenant key helpers.

Provides a lazily-initialized Redis connection pool and key-namespacing
utilities that enforce the per-tenant cache isolation convention:

    Key convention:  tenant:{tenant_id}:{part1}:{part2}:...

All platform components (session store, rate limiter, embedding cache,
webhook dedup) must use ``tenant_key()`` to build Redis keys.
"""

from __future__ import annotations

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import get_settings


class _RedisState:
    """Holds the lazily-initialized Redis client pool."""

    pool: Redis | None = None  # type: ignore[type-arg]


_state = _RedisState()


def initialize_redis() -> None:
    """Create the Redis connection pool.

    Must be called from the application lifespan startup handler.
    Uses ``redis.asyncio.from_url`` which returns a pool-backed client.
    """
    settings = get_settings()
    _state.pool = aioredis.from_url(
        settings.redis_url,
        encoding='utf-8',
        decode_responses=True,
        max_connections=20,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


async def dispose_redis() -> None:
    """Close the Redis connection pool.

    Must be called from the application lifespan shutdown handler.
    """
    if _state.pool is not None:
        await _state.pool.aclose()
        _state.pool = None


def get_redis() -> Redis:  # type: ignore[type-arg]
    """Return the active Redis client.

    Raises:
        RuntimeError: If ``initialize_redis()`` has not been called.
    """
    if _state.pool is None:
        raise RuntimeError('Redis not initialized. Call initialize_redis() from the app lifespan.')
    return _state.pool


def tenant_key(tenant_id: str, *parts: str) -> str:
    """Build a tenant-namespaced Redis key.

    All Redis keys used by the platform must be constructed with this helper
    to guarantee that tenant data never bleeds across namespace boundaries.

    Convention: ``tenant:{tenant_id}`` or ``tenant:{tenant_id}:{part1}:{part2}``

    Args:
        tenant_id: The tenant UUID string.
        *parts:    Additional path segments (e.g., ``"session"``, ``"<session_id>"``).

    Returns:
        A colon-delimited Redis key string.

    Examples::

        tenant_key("abc-123")                        → "tenant:abc-123"
        tenant_key("abc-123", "rate_limit")          → "tenant:abc-123:rate_limit"
        tenant_key("abc-123", "session", "sess-456") → "tenant:abc-123:session:sess-456"
        tenant_key("abc-123", "embed_cache", query)  → "tenant:abc-123:embed_cache:<query>"
    """
    if not parts:
        return f'tenant:{tenant_id}'
    return f"tenant:{tenant_id}:{':'.join(parts)}"


async def check_redis_health() -> bool:
    """Ping Redis to verify connectivity.

    Returns:
        ``True`` if Redis responds to PING, ``False`` otherwise.
    """
    try:
        result = await get_redis().ping()
        return bool(result)
    except Exception:
        return False
