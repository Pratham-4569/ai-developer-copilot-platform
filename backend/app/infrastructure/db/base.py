"""SQLAlchemy 2.0 declarative foundation for the AI Copilot Platform.

This module defines the single ``Base`` class and the four mandatory mixins
that **every** ORM model in the platform inherits from.  No model may be
written without first importing from this module.

Design commitments (all mandated by database.md):
    - All primary keys are UUID (version 4), generated application-side via
      ``gen_random_uuid()`` as a server default so that the application can
      pre-generate IDs for distributed inserts while the database retains the
      ability to generate them independently.
    - All timestamps are ``TIMESTAMP WITH TIME ZONE`` (``TIMESTAMPTZ``).
      PostgreSQL stores them as UTC internally; the ORM maps them to
      timezone-aware :class:`datetime.datetime` objects.  No naive datetimes
      are ever persisted.
    - ``updated_at`` is managed by SQLAlchemy's ``onupdate`` hook at the
      application layer rather than a database trigger.  This keeps behaviour
      portable across PostgreSQL and test fixtures and ensures the timestamp
      reflects the application's notion of "now" (which can be mocked in
      tests).
    - Soft deletion (``deleted_at``) is used for every entity that may be
      referenced by immutable audit records.  Hard deletion is enforced only
      after retention policies are applied by a background maintenance task.
    - ``tenant_id`` is a mandatory non-nullable UUID foreign key on every
      tenant-scoped table.  The repository base class (Phase 3.2) enforces a
      ``WHERE tenant_id = :tenant_id`` clause on every read, update, and
      delete operation.  The column and its index are established here so
      that the enforcement contract is unconditional at the schema level.

SQLAlchemy version: 2.0+ (``DeclarativeBase``, ``Mapped``, ``mapped_column``
API).  The legacy ``declarative_base()`` factory is not used.

Python version: 3.12+.  All type annotations use the built-in
``type | None`` union syntax.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Type annotation map
# ---------------------------------------------------------------------------
# ``DeclarativeBase`` allows a global type-annotation→SQLAlchemy-type mapping
# so that ``Mapped[uuid.UUID]`` and ``Mapped[datetime]`` resolve correctly to
# the PostgreSQL-native types without requiring explicit ``mapped_column``
# overrides on every column.
#
# ``PG_UUID(as_uuid=True)`` instructs asyncpg to return Python ``uuid.UUID``
# objects directly, avoiding unnecessary string round-trips.
#
# ``DateTime(timezone=True)`` maps to ``TIMESTAMP WITH TIME ZONE`` in
# PostgreSQL and instructs SQLAlchemy to return timezone-aware
# ``datetime.datetime`` objects with ``tzinfo=UTC``.

_TYPE_ANNOTATION_MAP: dict[type[Any], Any] = {
    uuid.UUID: PG_UUID(as_uuid=True),
    datetime: DateTime(timezone=True),
}


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models in the platform.

    All ORM models **must** inherit from this class (directly or via a mixin
    chain that terminates here).  Do not instantiate ``Base`` directly.

    The ``type_annotation_map`` ensures that:
    -   ``Mapped[uuid.UUID]``  →  ``UUID`` (PostgreSQL native)
    -   ``Mapped[datetime]``   →  ``TIMESTAMP WITH TIME ZONE``

    Alembic's ``env.py`` must reference ``Base.metadata`` as
    ``target_metadata`` so that autogenerate detects all models that import
    from this module.
    """

    type_annotation_map = _TYPE_ANNOTATION_MAP


# ---------------------------------------------------------------------------
# UUIDPrimaryKeyMixin
# ---------------------------------------------------------------------------

class UUIDPrimaryKeyMixin:
    """Mixin that adds a UUID v4 primary key column named ``id``.

    The ``id`` column is:
    -   ``UUID`` (PostgreSQL native, ``as_uuid=True`` → Python ``uuid.UUID``)
    -   ``NOT NULL``
    -   ``PRIMARY KEY``
    -   Server default: ``gen_random_uuid()``  — the database generates the
        UUID if the application does not supply one.  Application services
        **should** pre-generate UUIDs before insert (``uuid.uuid4()``) so that
        the ID is known before the row is committed and can be included in
        domain events without a round-trip.

    Usage::

        class TenantModel(UUIDPrimaryKeyMixin, Base):
            __tablename__ = "tenants"
            ...
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        # Allow the database to generate the UUID if the application does not.
        # In practice, application services always pre-generate UUIDs using
        # ``uuid.uuid4()`` before calling session.add(), so this server default
        # is a safety net, not the primary generation path.
        server_default=text("gen_random_uuid()"),
        nullable=False,
        comment="Surrogate primary key — UUID v4, generated application-side.",
    )


# ---------------------------------------------------------------------------
# TimestampMixin
# ---------------------------------------------------------------------------

class TimestampMixin:
    """Mixin that adds ``created_at`` and ``updated_at`` audit timestamps.

    Both columns are ``TIMESTAMP WITH TIME ZONE`` (``TIMESTAMPTZ``).

    ``created_at``
        Set once at insert time to the current UTC instant.  Never updated.

    ``updated_at``
        Mirrors ``created_at`` at insert time.  Updated automatically by
        SQLAlchemy's ``onupdate`` hook on every subsequent ``UPDATE``
        statement that touches any column in the row.  This is managed at the
        application layer (not via a database trigger) to maintain portability
        across environments and to allow test fixtures to control time.

    Both columns use ``datetime.now(timezone.utc)`` as the Python-side
    callable default, which means SQLAlchemy resolves the value at Python
    execution time rather than using a SQL expression.  This guarantees that
    the value stored in the database is the same value that the ORM object
    holds after flush — no desync between the application and the database
    clock, and no need for a post-insert refresh.

    Usage::

        class RepositoryModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
            __tablename__ = "repositories"
            ...
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC instant at which this row was first inserted.",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment=(
            "UTC instant at which this row was last modified.  "
            "Managed by the application layer via SQLAlchemy onupdate."
        ),
    )


# ---------------------------------------------------------------------------
# SoftDeleteMixin
# ---------------------------------------------------------------------------

class SoftDeleteMixin:
    """Mixin that adds a ``deleted_at`` soft-deletion timestamp.

    When ``deleted_at IS NULL`` the row is considered active.
    When ``deleted_at IS NOT NULL`` the row is considered deleted.

    Soft deletion is used for every entity that may be referenced by
    immutable audit records (``audit_log_entries``) or by other entities
    via foreign keys that must not be broken by hard deletion.  Hard
    deletion is performed only after data retention policies are enforced by
    the ``MaintenanceWorker`` background task.

    **Repository contract**: every concrete repository implementation that
    uses ``SoftDeleteMixin`` models **must** add
    ``WHERE deleted_at IS NULL`` to every read, update, and delete query.
    This is enforced by the repository base class (Phase 3.2).

    **Partial indexes**: each model that uses this mixin should declare a
    partial index ``WHERE deleted_at IS NULL`` on its most-queried lookup
    columns (e.g., ``tenant_id``, ``status``) to avoid scanning deleted rows.
    These indexes are declared on the concrete model classes, not here, because
    they reference table-specific columns.

    Usage::

        class UserModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
            __tablename__ = "users"
            ...

        # Query pattern enforced by the repository layer:
        # SELECT * FROM users WHERE tenant_id = :tid AND deleted_at IS NULL
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment=(
            "UTC instant at which this row was soft-deleted.  "
            "NULL means the record is active.  "
            "Set by the repository delete method; never by direct column assignment."
        ),
    )


# ---------------------------------------------------------------------------
# TenantScopedMixin
# ---------------------------------------------------------------------------

class TenantScopedMixin:
    """Mixin that adds a mandatory ``tenant_id`` foreign key column.

    This mixin is the data-model enforcement point for the platform's
    shared-database, shared-schema multi-tenancy strategy (database.md §2).

    ``tenant_id``
        -   ``UUID NOT NULL`` — every tenant-scoped row must belong to a tenant.
        -   Foreign key to ``tenants.id`` with ``ondelete="RESTRICT"`` —
            prevents accidental deletion of a tenant that still owns data.
        -   Indexed — ``idx_{tablename}_tenant_id`` partial index declared on
            the concrete model class via ``__table_args__`` (see below for
            the helper method).  This mixin creates the column; models are
            responsible for declaring the index.

    **Isolation contract**: the SQLAlchemy repository base class (Phase 3.2)
    injects ``WHERE tenant_id = :tenant_id`` on *every* read, update, and
    delete operation.  No service may call a repository method without
    supplying an authenticated tenant context.  Cross-tenant queries are
    architecturally impossible at the infrastructure layer.

    **Index guidance**: models inheriting this mixin should add a partial
    index on ``(tenant_id)`` where ``deleted_at IS NULL`` (for soft-deleted
    models) or an unconditional index otherwise.  Use the
    ``build_tenant_index`` class-method helper below to generate a
    consistently named index.

    Usage::

        class RepositoryModel(
            UUIDPrimaryKeyMixin,
            TimestampMixin,
            SoftDeleteMixin,
            TenantScopedMixin,
            Base,
        ):
            __tablename__ = "repositories"

            __table_args__ = (
                TenantScopedMixin.build_tenant_index("repositories"),
                # ...additional indexes...
            )
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="RESTRICT",
            name="fk_%(tablename)s_tenant_id",  # Alembic-resolvable naming convention
        ),
        nullable=False,
        index=False,  # Index is declared explicitly per-model via __table_args__
        comment=(
            "FK → tenants.id.  "
            "Row-level tenant isolation enforced by the repository base class.  "
            "Never NULL; every row belongs to exactly one tenant."
        ),
    )

    @classmethod
    def build_tenant_index(
        cls,
        table_name: str,
        *,
        soft_deleted: bool = True,
    ) -> Index:
        """Build a consistently named, optionally partial index on ``tenant_id``.

        Args:
            table_name: The ``__tablename__`` of the model declaring this index.
                Used to generate a unique index name following the project's
                naming convention: ``idx_{table_name}_tenant_id``.
            soft_deleted: When ``True`` (default), the index is a partial index
                with ``postgresql_where="deleted_at IS NULL"``.  Set to
                ``False`` for models that do not use :class:`SoftDeleteMixin`
                (e.g., ``user_roles``, ``role_permissions``).

        Returns:
            A :class:`sqlalchemy.Index` instance ready to be placed in
            ``__table_args__``.

        Example::

            __table_args__ = (
                TenantScopedMixin.build_tenant_index("repositories"),
            )
        """
        index_name = f"idx_{table_name}_tenant_id"
        if soft_deleted:
            return Index(
                index_name,
                "tenant_id",
                postgresql_where=text("deleted_at IS NULL"),
            )
        return Index(index_name, "tenant_id")


# ---------------------------------------------------------------------------
# Convenience re-export for Alembic env.py
# ---------------------------------------------------------------------------
# Alembic's env.py must reference ``Base.metadata`` as ``target_metadata``.
# Importing ``Base`` from this module is sufficient; no separate metadata
# export is required.  This comment is here to document the expected import
# pattern for future maintainers:
#
#     from app.infrastructure.db.base import Base
#     target_metadata = Base.metadata
#
# All ORM model files (auth_models.py, tenant_models.py, …) must be imported
# in alembic/env.py *before* ``target_metadata`` is referenced, so that
# SQLAlchemy has registered all table definitions into ``Base.metadata``.

__all__ = [
    "Base",
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "TenantScopedMixin",
]
