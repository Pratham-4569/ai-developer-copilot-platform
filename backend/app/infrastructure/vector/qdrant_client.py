"""Qdrant async client factory and collection naming helpers.

All vector store operations go through this module. The Qdrant client is
initialized once at startup and shared across all request handlers.

Collection naming convention:
    ``tenant_{tenant_id}_repo_{repository_id}``

UUIDs are stored with hyphens replaced by underscores because Qdrant
collection names must match ``[a-zA-Z0-9_-]+`` and hyphens in UUIDs
can cause confusion with Qdrant's internal naming patterns.

The RAG service is the sole consumer of the Qdrant client — no other
module should import or call the client directly.
"""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient

from app.config import get_settings


class _QdrantState:
    """Holds the lazily-initialized Qdrant async client."""

    client: AsyncQdrantClient | None = None


_state = _QdrantState()


def initialize_qdrant() -> None:
    """Create the Qdrant async client.

    Must be called from the application lifespan startup handler.
    Passes ``api_key`` only when ``QDRANT_API_KEY`` is configured;
    omitting it allows unauthenticated local Qdrant instances.
    """
    settings = get_settings()
    kwargs: dict[str, object] = {'url': settings.qdrant_url}
    if settings.qdrant_api_key:
        kwargs['api_key'] = settings.qdrant_api_key
    _state.client = AsyncQdrantClient(**kwargs)


async def dispose_qdrant() -> None:
    """Close the Qdrant async client.

    Must be called from the application lifespan shutdown handler.
    """
    if _state.client is not None:
        await _state.client.close()
        _state.client = None


def get_qdrant_client() -> AsyncQdrantClient:
    """Return the active Qdrant async client.

    Raises:
        RuntimeError: If ``initialize_qdrant()`` has not been called.
    """
    if _state.client is None:
        raise RuntimeError(
            'Qdrant not initialized. Call initialize_qdrant() from the app lifespan.'
        )
    return _state.client


def collection_name(tenant_id: str, repository_id: str) -> str:
    """Build the Qdrant collection name for a tenant/repository pair.

    Hyphens in UUIDs are replaced with underscores to produce valid,
    unambiguous Qdrant collection names.

    Convention: ``tenant_{tenant_id}_repo_{repository_id}``

    Args:
        tenant_id:     The tenant UUID string.
        repository_id: The repository UUID string.

    Returns:
        A Qdrant-safe collection name string.

    Example::

        collection_name(
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        )
        # → "tenant_550e8400_e29b_41d4_a716_446655440000_repo_6ba7b810_9dad_11d1_80b4_00c04fd430c8"
    """
    safe_tenant = tenant_id.replace('-', '_')
    safe_repo = repository_id.replace('-', '_')
    return f'tenant_{safe_tenant}_repo_{safe_repo}'


async def check_qdrant_health() -> bool:
    """Verify Qdrant connectivity by listing collections.

    Returns:
        ``True`` if Qdrant responds, ``False`` if the client is
        uninitialized or the request fails.
    """
    try:
        await get_qdrant_client().get_collections()
        return True
    except Exception:
        return False
