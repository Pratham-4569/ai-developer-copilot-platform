"""Async SQLAlchemy engine and session factory.

Provides two session factories:
    async_session_write — primary path, routes through PgBouncer.
    async_session_read  — read path (same PgBouncer pool in Phase 2;
                          swap engine for a read replica in production).

PgBouncer compatibility requirements (transaction pooling mode):
    - ``prepared_statement_cache_size=0``: disables asyncpg's named prepared
      statement cache. PgBouncer does not support named prepared statements
      across pool connections in transaction mode.
    - ``server_settings={'jit': 'off'}``: prevents JIT compilation overhead
      on pooled connections from unexpected GUC changes.

Sessions are never exposed outside the infrastructure layer. Application
services receive sessions via dependency injection only.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


def _make_engine(url: str) -> AsyncEngine:
    """Create a PgBouncer-compatible async SQLAlchemy engine.

    Args:
        url: An ``asyncpg`` connection URL
             (``postgresql+asyncpg://user:pass@host:port/db``).

    Returns:
        A configured :class:`AsyncEngine`.
    """
    return create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,  # Detect stale connections before handing them out
        pool_size=5,         # Persistent connections per process
        max_overflow=10,     # Burst capacity above pool_size
        connect_args={
            # Disable asyncpg's named prepared statement cache.
            # PgBouncer transaction mode routes each statement to any backend
            # connection, making named prepared statements invalid.
            'prepared_statement_cache_size': 0,
            # Disable server-side JIT; avoids unexpected per-connection GUC
            # state that PgBouncer cannot reset between pooled transactions.
            'server_settings': {'jit': 'off'},
        },
    )


class _DbState:
    """Holds lazy-initialized engine and session factory references."""

    engine_write: AsyncEngine | None = None
    engine_read: AsyncEngine | None = None
    session_write: async_sessionmaker[AsyncSession] | None = None
    session_read: async_sessionmaker[AsyncSession] | None = None


_state = _DbState()


def initialize_db() -> None:
    """Initialize engines and session factories.

    Must be called once from the application lifespan startup handler.
    Phase 2 routes both write and read through the same PgBouncer pool.
    A separate read-replica URL can be introduced in later phases by wiring
    a second engine to ``_state.engine_read``.
    """
    settings = get_settings()

    _state.engine_write = _make_engine(settings.database_url)
    # Phase 2: read and write share the same PgBouncer pool.
    # Replace with a replica URL in production when read-replica is available.
    _state.engine_read = _state.engine_write

    _state.session_write = async_sessionmaker(
        _state.engine_write,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    _state.session_read = async_sessionmaker(
        _state.engine_read,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def dispose_db() -> None:
    """Dispose connection pools.

    Must be called from the application lifespan shutdown handler.
    """
    if _state.engine_write is not None:
        await _state.engine_write.dispose()
    if _state.engine_read is not None and _state.engine_read is not _state.engine_write:
        await _state.engine_read.dispose()
    _state.engine_write = None
    _state.engine_read = None
    _state.session_write = None
    _state.session_read = None


@asynccontextmanager
async def get_write_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a write-path :class:`AsyncSession`.

    Commits on clean exit; rolls back and re-raises on any exception.
    Routes through PgBouncer to the primary PostgreSQL instance.

    Usage::

        async with get_write_session() as session:
            session.add(entity)
    """
    assert _state.session_write is not None, (
        'Database not initialized. Call initialize_db() from the app lifespan.'
    )
    async with _state.session_write() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_read_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a read-path :class:`AsyncSession`.

    No commit is performed. Routes to the read replica when one is configured,
    otherwise uses the same PgBouncer pool as the write path.

    Usage::

        async with get_read_session() as session:
            result = await session.execute(select(Model))
    """
    assert _state.session_read is not None, (
        'Database not initialized. Call initialize_db() from the app lifespan.'
    )
    async with _state.session_read() as session:
        yield session


async def check_db_health() -> bool:
    """Execute a trivial query to verify PostgreSQL connectivity.

    Returns:
        ``True`` if the database responds within the caller's timeout,
        ``False`` if the session is uninitialized or the query fails.
    """
    if _state.session_read is None:
        return False
    try:
        async with get_read_session() as session:
            await session.execute(text('SELECT 1'))
        return True
    except Exception:
        return False
