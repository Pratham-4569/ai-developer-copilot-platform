"""ORM models for the Tenant Management domain — Phase 3.4: Database Layer.

Tables implemented
------------------
- ``tenants``         — root tenant (organisation) record; no tenant_id FK
- ``tenant_settings`` — per-tenant configuration; one-to-one with tenants

Design commitments
------------------
- ``tenants`` is NOT itself tenant-scoped; it IS the isolation boundary.
  It therefore does not inherit :class:`~app.infrastructure.db.base.TenantScopedMixin`.
- ``tenant_settings.tenant_id`` is UNIQUE, enforcing the one-to-one relationship
  at the schema level.
- The ``updated_by`` column on ``tenant_settings`` is a forward-reference FK to
  ``users.id`` (defined in ``auth_models.py``).  SQLAlchemy resolves this via the
  string-based ``ForeignKey`` plus ``use_alter=True`` so that Alembic can emit
  ``ALTER TABLE … ADD CONSTRAINT`` after both tables are created, breaking the
  circular DDL dependency.
- JSONB columns use ``sqlalchemy.dialects.postgresql.JSONB`` for native PostgreSQL
  JSON operations (containment, path expressions, GIN indexing).
- All ``VARCHAR`` lengths follow the exact widths specified in ``database.md``.
- ``CHECK`` constraints replicate the schema-level guard rails from ``database.md``
  and are named following the project convention ``ck_{tablename}_{column}``.

References
----------
- docs/database.md — §6 "Tenant Management Tables"
- docs/roadmap.md  — Phase 3 "Database Layer"
- app/infrastructure/db/base.py — ``Base``, ``UUIDPrimaryKeyMixin``,
  ``TimestampMixin``, ``SoftDeleteMixin``
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


# ---------------------------------------------------------------------------
# TenantModel
# ---------------------------------------------------------------------------

class TenantModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """ORM model for the ``tenants`` table.

    Represents a single organisation (tenant) on the platform.  Every user,
    repository, analysis result, and configuration record is scoped to a
    tenant via a ``tenant_id`` foreign key on those tables.

    ``TenantModel`` itself has no ``tenant_id`` column — it IS the isolation
    root.  The ``TenantScopedMixin`` is intentionally NOT applied here.

    Soft deletion is supported: ``deleted_at IS NOT NULL`` means the tenant
    is deactivated.  Hard deletion is deferred until retention policies are
    enforced by the maintenance worker.

    Plan enforcement
    ----------------
    ``max_repositories`` and ``max_users`` are plan-enforced limits evaluated
    by the application service layer, not by database constraints, because
    limit changes must take effect immediately without schema migrations.

    Relationships
    -------------
    ``settings``   — back-populates :class:`TenantSettingsModel`.
    ``users``      — one-to-many; populated by ``UserModel.tenant``.
    ``user_roles`` — one-to-many; populated by ``UserRoleModel.tenant``.
    ``refresh_tokens`` — one-to-many; populated by ``RefreshTokenModel.tenant``.
    """

    __tablename__ = "tenants"

    # ----- Columns ----------------------------------------------------------

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment=(
            "URL-safe organisation identifier; lowercase, hyphens only.  "
            "Used as the subdomain or path prefix in multi-tenant routing."
        ),
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable organisation name shown in the UI.",
    )

    plan: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'free'"),
        comment="Subscription plan tier.  Checked by services to enforce feature limits.",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment="FALSE means the tenant is suspended; all API calls return 403.",
    )

    max_repositories: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("10"),
        comment="Plan-enforced upper bound on connected repositories.",
    )

    max_users: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("5"),
        comment="Plan-enforced upper bound on active user accounts.",
    )

    data_region: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'us'"),
        comment=(
            "Data residency region.  Controls which Qdrant cluster, object storage "
            "bucket, and Redis instance the tenant's data is written to."
        ),
    )

    # ----- Constraints & Indexes --------------------------------------------

    __table_args__ = (
        CheckConstraint(
            "plan IN ('free', 'pro', 'enterprise')",
            name="ck_tenants_plan",
        ),
        CheckConstraint(
            "data_region IN ('us', 'eu')",
            name="ck_tenants_data_region",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_at > created_at",
            name="ck_tenants_deleted_at_after_created_at",
        ),
        # Partial index: fast tenant-by-slug lookup, skips soft-deleted tenants.
        Index("idx_tenants_slug", "slug", postgresql_where=text("deleted_at IS NULL")),
    )

    # ----- Relationships ----------------------------------------------------

    settings: Mapped[TenantSettingsModel] = relationship(
        "TenantSettingsModel",
        back_populates="tenant",
        uselist=False,
        lazy="raise",  # Always load explicitly; prevents N+1 on tenant lists.
        cascade="all, delete-orphan",
    )

    # Forward references for relationships defined in auth_models.py.
    # These are populated when auth_models is imported; kept as strings to
    # avoid circular import at module level.
    users: Mapped[list[Any]] = relationship(
        "UserModel",
        back_populates="tenant",
        lazy="raise",
        foreign_keys="UserModel.tenant_id",
    )

    user_roles: Mapped[list[Any]] = relationship(
        "UserRoleModel",
        back_populates="tenant",
        lazy="raise",
        foreign_keys="UserRoleModel.tenant_id",
    )

    refresh_tokens: Mapped[list[Any]] = relationship(
        "RefreshTokenModel",
        back_populates="tenant",
        lazy="raise",
        foreign_keys="RefreshTokenModel.tenant_id",
    )

    def __repr__(self) -> str:
        return f"<TenantModel id={self.id!r} slug={self.slug!r} plan={self.plan!r}>"


# ---------------------------------------------------------------------------
# TenantSettingsModel
# ---------------------------------------------------------------------------

# Default value for ``enabled_agents`` column.
# Stored as a server-side default expression so that rows inserted via
# raw SQL (migrations, test fixtures) also receive the correct default.
_ENABLED_AGENTS_DEFAULT = (
    '{"architecture": true, "code_review": true, "bug_detection": true, '
    '"security": true, "documentation": true, "test_generation": true, '
    '"issue_generation": true, "refactoring": true}'
)

# Default severity thresholds — one entry per agent type.
_SEVERITY_THRESHOLDS_DEFAULT = (
    '{"architecture": "medium", "code_review": "low", "bug_detection": "low", '
    '"security": "low", "documentation": "medium", "test_generation": "medium", '
    '"issue_generation": "medium", "refactoring": "medium"}'
)


class TenantSettingsModel(UUIDPrimaryKeyMixin, Base):
    """ORM model for the ``tenant_settings`` table.

    Stores per-tenant configuration that controls AI agent behaviour, PR
    review automation, rate limits, data retention, and notification
    preferences.  Changes take effect immediately without code deployments.

    One-to-one relationship with :class:`TenantModel`: the ``UNIQUE``
    constraint on ``tenant_id`` is enforced at both the schema level
    (``UniqueConstraint``) and the relationship level (``uselist=False``
    on ``TenantModel.settings``).

    ``updated_at`` is managed here manually (not via ``TimestampMixin``)
    because this table has no ``created_at`` column in the schema spec and
    the ``updated_by`` foreign key to ``users.id`` introduces a circular
    dependency that requires ``use_alter=True``.  The ``TimestampMixin``
    would add ``created_at``, which is correct — we include it here for
    auditability even though the spec does not mandate it.

    Forward reference
    -----------------
    ``updated_by`` references ``users.id``.  ``UserModel`` is defined in
    ``auth_models.py``, which imports from this module.  The FK is declared
    with ``use_alter=True`` so that Alembic emits the constraint as a
    post-creation ``ALTER TABLE`` statement, avoiding circular DDL.
    """

    __tablename__ = "tenant_settings"

    # ----- Columns ----------------------------------------------------------

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
            name="fk_tenant_settings_tenant_id",
        ),
        nullable=False,
        comment=(
            "FK → tenants.id.  Uniqueness is enforced by "
            "uq_tenant_settings_tenant_id in __table_args__."
        ),
    )

    # --- Agent toggles ---
    enabled_agents: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text(f"'{_ENABLED_AGENTS_DEFAULT}'::jsonb"),
        comment=(
            "Boolean map of agent_type → enabled.  "
            "Disabled agents are skipped by the analysis orchestration service."
        ),
    )

    severity_thresholds: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text(f"'{_SEVERITY_THRESHOLDS_DEFAULT}'::jsonb"),
        comment=(
            "Map of agent_type → minimum severity string for the agent to report.  "
            "Findings below the threshold are silently dropped at the agent output stage."
        ),
    )

    # --- PR review settings ---
    pr_review_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment="When TRUE, GitHub PR webhooks trigger inline code review comments.",
    )

    pr_block_on_critical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
        comment=(
            "When TRUE, a PR review containing Critical findings posts a "
            "'REQUEST_CHANGES' verdict instead of 'COMMENT'."
        ),
    )

    # --- Analysis automation ---
    auto_analysis_on_push: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment="When TRUE, a GitHub push event triggers an incremental analysis job.",
    )

    auto_analysis_on_pr: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment="When TRUE, a GitHub pull_request opened/synchronize event triggers a PR-scoped analysis.",
    )

    # --- Rate limits & retention ---
    api_rate_limit_per_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("60"),
        comment="Per-tenant API rate limit enforced by the rate-limit middleware via Redis.",
    )

    chat_session_ttl_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("24"),
        comment=(
            "Redis TTL for active chat session state.  After expiry the session "
            "is hydrated from PostgreSQL on next access."
        ),
    )

    analysis_retention_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("365"),
        comment="Number of days after which completed analysis jobs and findings are archived.",
    )

    # --- Audit ---
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="UTC instant of the most recent settings change.",
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        # use_alter=True defers the FK constraint to a post-CREATE ALTER TABLE
        # statement, breaking the circular dependency between tenant_settings
        # and users (users.tenant_id → tenants.id, tenant_settings.updated_by
        # → users.id).  Alembic generates this correctly when use_alter=True
        # is set.
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_tenant_settings_updated_by",
            use_alter=True,
        ),
        nullable=True,
        comment=(
            "FK → users.id of the admin who last modified these settings.  "
            "NULL for system-applied defaults."
        ),
    )

    # ----- Constraints & Indexes --------------------------------------------

    __table_args__ = (
        # Single, explicitly-named unique constraint on tenant_id.
        # This enforces the one-to-one relationship with tenants at the
        # schema level.  'unique=True' is intentionally NOT set on the
        # mapped_column above: doing so would produce a second anonymous
        # unique index alongside this named one, wasting storage and
        # confusing Alembic autogenerate comparison on re-runs.
        UniqueConstraint("tenant_id", name="uq_tenant_settings_tenant_id"),
    )

    # ----- Relationships ----------------------------------------------------

    tenant: Mapped[TenantModel] = relationship(
        "TenantModel",
        back_populates="settings",
        lazy="raise",
    )

    updated_by_user: Mapped[Any | None] = relationship(
        "UserModel",
        foreign_keys=[updated_by],
        lazy="raise",
    )

    def __repr__(self) -> str:
        return (
            f"<TenantSettingsModel id={self.id!r} "
            f"tenant_id={self.tenant_id!r}>"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "TenantModel",
    "TenantSettingsModel",
]
