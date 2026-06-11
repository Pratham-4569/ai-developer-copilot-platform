"""Alembic async migration environment — Phase 3.2: Database Layer.

Runtime behaviour
-----------------
Alembic connects **directly** to PostgreSQL, bypassing PgBouncer.
PgBouncer in transaction-pooling mode is incompatible with the advisory
locks and DDL statements issued by Alembic migrations.  This is why a
separate ``DATABASE_DIRECT_URL`` environment variable exists in the
platform topology.

Connection URL resolution order
--------------------------------
1. ``DATABASE_DIRECT_URL`` environment variable (preferred — set in CI/CD
   and local Docker Compose via ``.env``).
2. ``sqlalchemy.url`` value from ``alembic.ini`` (fallback — acceptable
   only for local Docker Compose where both URLs resolve to the same host).

The application URL (``DATABASE_URL``, routed through PgBouncer) is never
used here.

Async engine
-------------
``asyncpg`` is the driver; migrations run on a ``NullPool`` engine so that
each ``alembic upgrade`` invocation holds exactly one connection and
releases it cleanly on exit.  The ``asyncio.run()`` wrapper satisfies
Alembic's synchronous process entry point while running the migration
coroutine on a fresh event loop.

Autogenerate
------------
``target_metadata = Base.metadata`` is required for
``alembic revision --autogenerate`` to detect schema drift.  All ORM model
files (e.g., ``auth_models.py``, ``tenant_models.py``) must be imported
below, **before** the ``target_metadata`` assignment, so that SQLAlchemy
has registered every ``Table`` object into ``Base.metadata``.  Currently no
models exist (Phase 3.2 foundation only); imports will be added here as
models are created.

References
----------
- docs/database.md — §3 "Alembic migration strategy"
- docs/architecture.md — §5 "Two-URL topology (PgBouncer vs direct)"
- alembic.ini — ``sqlalchemy.url`` comment block
- app/infrastructure/db/session.py — ``_make_engine`` (application path)
"""

from __future__ import annotations

import asyncio
import logging
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to values within alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# ---------------------------------------------------------------------------
# Logging — configure from alembic.ini [loggers] / [handlers] / [formatters]
# ---------------------------------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# ---------------------------------------------------------------------------
# Override sqlalchemy.url with DATABASE_DIRECT_URL from the environment.
#
# DATABASE_DIRECT_URL must point directly at PostgreSQL (not PgBouncer).
# If the variable is absent, the value already present in alembic.ini is
# used as-is, which is acceptable for local Docker Compose development where
# both paths resolve to the same PostgreSQL instance.
# ---------------------------------------------------------------------------
_direct_url: str | None = os.environ.get("DATABASE_DIRECT_URL")
if _direct_url:
    config.set_main_option("sqlalchemy.url", _direct_url)
    logger.debug(
        "alembic.env: using DATABASE_DIRECT_URL from environment",
        extra={"url_host": _direct_url.split("@")[-1] if "@" in _direct_url else "<no-host>"},
    )
else:
    logger.debug(
        "alembic.env: DATABASE_DIRECT_URL not set; "
        "using sqlalchemy.url from alembic.ini"
    )

# ---------------------------------------------------------------------------
# ORM model imports — populate Base.metadata for autogenerate.
#
# Add one import per model module here as models are introduced in Phase 3.2+.
# The import order does not matter; SQLAlchemy collects all Table objects
# from all imported modules into Base.metadata automatically.
#
# Example (do not un-comment until the module exists):
#   from app.infrastructure.db.models import tenant_models  # noqa: F401
#   from app.infrastructure.db.models import auth_models    # noqa: F401
# ---------------------------------------------------------------------------
from app.infrastructure.db.base import Base  # noqa: E402

# ---------------------------------------------------------------------------
# target_metadata — required for autogenerate and offline SQL rendering.
# ---------------------------------------------------------------------------
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration runner
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    In offline mode Alembic does **not** connect to the database; it
    generates a SQL script that a DBA can review and execute manually.
    This is useful for environments where direct database access is
    restricted (e.g., production deployments gated by a change-management
    process).

    The ``dialect_name`` is inferred from the URL scheme; because our URL
    always begins with ``postgresql+asyncpg://``, Alembic renders
    PostgreSQL-flavoured DDL.  ``literal_binds=True`` causes bound
    parameters to be rendered as literals in the SQL output rather than as
    ``%s`` placeholders.

    Usage::

        alembic upgrade head --sql        # prints SQL to stdout
        alembic upgrade head --sql > migration.sql  # redirect to file
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        # Render named (as opposed to positional) parameter style so the
        # generated SQL script is readable and directly executable.
        dialect_opts={"paramstyle": "named"},
        # Include full schema name in generated DDL when schema is set.
        include_schemas=True,
        # Compare server defaults to detect drift from server-side defaults
        # (e.g., gen_random_uuid()).
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration runner (async)
# ---------------------------------------------------------------------------

def _do_run_migrations(connection: Connection) -> None:
    """Configure the migration context and run pending migrations.

    Called synchronously inside ``run_sync`` from the async runner below.
    This function must be synchronous because ``context.run_migrations()``
    is a synchronous Alembic API.

    Args:
        connection: A live, synchronous-compatible DBAPI connection
            provided by ``AsyncEngine.connect()`` → ``run_sync``.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Compare server defaults so autogenerate detects changes to
        # server_default expressions (e.g., gen_random_uuid()).
        compare_server_default=True,
        # Include full schema name in generated DDL.
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    """Create an async engine, acquire a connection, and run migrations.

    Uses ``NullPool`` to ensure no connection is held after the migration
    process exits.  Pooling is not beneficial in a short-lived migration
    CLI process and can mask teardown issues in test environments.

    The engine is disposed immediately after migrations finish to release
    all resources before the process exits.
    """
    # Build engine configuration from alembic.ini, with the URL already
    # overridden by DATABASE_DIRECT_URL if present.
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(_do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    This is the default mode used by ``alembic upgrade head`` without the
    ``--sql`` flag.  A real database connection is established and
    migrations are executed immediately.

    The asyncio event loop is created by ``asyncio.run()``.  Alembic
    invokes this function from a synchronous CLI context, so
    ``asyncio.run()`` is the correct entry point — **not**
    ``loop.run_until_complete()``, which is deprecated in Python 3.10+.
    """
    asyncio.run(_run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point — delegated to offline or online runner by Alembic.
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
