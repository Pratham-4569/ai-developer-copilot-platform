"""FastAPI application factory.

Infrastructure clients are initialized in the lifespan context manager so
that they are available for the full request lifecycle and disposed cleanly
on shutdown. Initialization order: DB → Redis → Qdrant → Storage → LLM →
Embedding. Shutdown order is the reverse.

No business logic lives here — the factory only wires middleware, routers,
and the infrastructure lifecycle.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.config import get_settings
from app.infrastructure.cache.redis_client import dispose_redis, initialize_redis
from app.infrastructure.db.session import dispose_db, initialize_db
from app.infrastructure.llm.embedding_adapter import dispose_embedding, initialize_embedding
from app.infrastructure.llm.llm_adapter import dispose_llm, initialize_llm
from app.infrastructure.storage.object_storage_adapter import initialize_storage
from app.infrastructure.vector.qdrant_client import dispose_qdrant, initialize_qdrant
from app.interfaces.api.v1.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and dispose all infrastructure clients around the app lifecycle.

    Startup order:
        1. Database (PgBouncer → PostgreSQL)
        2. Redis
        3. Qdrant
        4. Object Storage
        5. LLM adapter
        6. Embedding adapter

    Shutdown order is the reverse of startup so that dependent clients are
    torn down before their dependencies.
    """
    logger.info('Starting up: initializing infrastructure clients')

    initialize_db()
    logger.info('Database session factory initialized (via PgBouncer)')

    initialize_redis()
    logger.info('Redis connection pool initialized')

    initialize_qdrant()
    logger.info('Qdrant async client initialized')

    initialize_storage()
    logger.info('Object storage adapter initialized')

    initialize_llm()
    logger.info('LLM adapter initialized')

    initialize_embedding()
    logger.info('Embedding adapter initialized')

    logger.info('All infrastructure clients ready — application is live')

    yield

    logger.info('Shutting down: disposing infrastructure clients')

    await dispose_embedding()
    await dispose_llm()
    await dispose_qdrant()
    await dispose_redis()
    await dispose_db()

    logger.info('All infrastructure clients disposed — shutdown complete')


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured :class:`FastAPI` instance ready for ``uvicorn``.
    """
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version='1.0.0',
        lifespan=lifespan,
        docs_url='/api/docs',
        redoc_url='/api/redoc',
        openapi_url='/api/openapi.json',
    )

    # Mount the v1 API router — all resource endpoints live under /api/v1
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    return application


app = create_app()
