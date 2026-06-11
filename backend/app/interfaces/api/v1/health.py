"""Health check endpoint.

``GET /health`` — verifies connectivity to PostgreSQL (via PgBouncer),
Redis, and Qdrant. All three probes run concurrently with a 2-second
per-probe timeout.

Response contract:
    200 OK  → ``{"status": "healthy", "services": {...}}``   — all green
    200 OK  → ``{"status": "degraded", "services": {...}}``  — one or more down

The endpoint always returns 200 so that load balancers and orchestrators
do not flap the instance out of rotation on a partial outage. Individual
service failures are surfaced in the response body for alerting.

Object storage is intentionally excluded from this probe — its connectivity
is validated separately during repository ingestion, not on every request.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.infrastructure.cache.redis_client import check_redis_health
from app.infrastructure.db.session import check_db_health
from app.infrastructure.vector.qdrant_client import check_qdrant_health

router = APIRouter(tags=['Health'])

_PROBE_TIMEOUT_SECONDS: float = 2.0

ServiceStatus = Literal['ok', 'error']


class ServiceHealth(BaseModel):
    """Per-service connectivity status."""

    database: ServiceStatus
    redis: ServiceStatus
    qdrant: ServiceStatus


class HealthResponse(BaseModel):
    """Top-level health check response payload."""

    status: Literal['healthy', 'degraded']
    services: ServiceHealth


async def _probe(coro: object) -> ServiceStatus:
    """Run a health-check coroutine with a timeout.

    Args:
        coro: An awaitable that returns ``bool``.

    Returns:
        ``'ok'`` if the coroutine returns ``True`` within the timeout,
        ``'error'`` on ``False``, timeout, or any exception.
    """
    try:
        result = await asyncio.wait_for(coro, timeout=_PROBE_TIMEOUT_SECONDS)  # type: ignore[arg-type]
        return 'ok' if result else 'error'
    except Exception:
        return 'error'


@router.get(
    '/health',
    response_model=HealthResponse,
    summary='Platform health check',
    description=(
        'Concurrently probes PostgreSQL (via PgBouncer), Redis, and Qdrant. '
        'Always returns HTTP 200. Use the ``status`` field to detect degraded state.'
    ),
)
async def health_check() -> HealthResponse:
    """Probe all data-service connections and return a structured health report."""
    db_status, redis_status, qdrant_status = await asyncio.gather(
        _probe(check_db_health()),
        _probe(check_redis_health()),
        _probe(check_qdrant_health()),
    )

    services = ServiceHealth(
        database=db_status,
        redis=redis_status,
        qdrant=qdrant_status,
    )
    overall: Literal['healthy', 'degraded'] = (
        'healthy'
        if db_status == 'ok' and redis_status == 'ok' and qdrant_status == 'ok'
        else 'degraded'
    )
    return HealthResponse(status=overall, services=services)
