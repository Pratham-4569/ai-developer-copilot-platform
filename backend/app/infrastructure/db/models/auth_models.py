"""ORM models for the Authentication & RBAC domain — Phase 3.4: Database Layer.

Tables implemented
------------------
- ``users``           — user accounts scoped to a tenant
- ``roles``           — system-defined platform roles (global, not tenant-scoped)
- ``permissions``     — granular action-resource permission definitions (global)
- ``role_permissions``— many-to-many join: roles → permissions (global)
- ``user_roles``      — role assignment for a user within a tenant (tenant-scoped)
- ``refresh_tokens``  — hashed JWT refresh tokens with family-based reuse detection

Design commitments
------------------
- ``users`` inherits ``TenantScopedMixin``: every row carries ``tenant_id``.
  Email uniqueness is **per-tenant**, not global.  The partial unique index on
  ``(tenant_id, email) WHERE deleted_at IS NULL`` enforces this without blocking
  soft-deleted email addresses from being re-used.

- ``roles`` and ``permissions`` are **global** (system-defined, platform-level).
  They do NOT carry a ``tenant_id`` and are loaded once at startup by
  ``RBACService`` and cached in Redis.  Tenant admins may not create custom roles
  in this iteration (PRD §2 three-role model).

- ``user_roles`` is **tenant-scoped**: the same user could theoretically hold
  different roles in different tenants (future-proof).  The active-assignment
  unique constraint ``(tenant_id, user_id, role_id) WHERE revoked_at IS NULL``
  prevents duplicate active grants.

- ``refresh_tokens.token_hash`` stores a SHA-256 hex digest of the raw token
  (never the raw token).  The ``family_id`` UUID groups all rotations of the
  same original token for server-side reuse detection.

- ``refresh_tokens.ip_address`` uses the PostgreSQL ``INET`` type via
  ``sqlalchemy.dialects.postgresql.INET``, which accepts both IPv4 and IPv6.

Circular FK resolution
----------------------
``tenant_settings.updated_by`` → ``users.id`` (in tenant_models.py) is declared
with ``use_alter=True``.  This module defines ``UserModel`` after
``tenant_models.py`` is imported; SQLAlchemy resolves the back-reference
correctly when both modules are fully loaded (which happens when the package
``__init__`` imports both).

References
----------
- docs/database.md — §5 "Authentication & RBAC Tables"
- docs/roadmap.md  — Phase 3 "Database Layer" and Phase 4a "Authentication & RBAC"
- app/infrastructure/db/base.py — mixin classes
- app/infrastructure/db/models/tenant_models.py — ``TenantModel``
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import (
    Base,
    SoftDeleteMixin,
    TenantScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


# ---------------------------------------------------------------------------
# role_permissions — pure association table (no ORM class needed)
# ---------------------------------------------------------------------------
# The join table between roles and permissions has only two FK columns and a
# composite PK.  A plain ``Table`` object is sufficient; an ORM class would
# add overhead with no benefit because services never instantiate this entity
# directly — they load the permission matrix via a JOIN at startup.

role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        PG_UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE", name="fk_role_permissions_role_id"),
        primary_key=True,
        nullable=False,
        comment="FK → roles.id.",
    ),
    Column(
        "permission_id",
        PG_UUID(as_uuid=True),
        ForeignKey(
            "permissions.id",
            ondelete="CASCADE",
            name="fk_role_permissions_permission_id",
        ),
        primary_key=True,
        nullable=False,
        comment="FK → permissions.id.",
    ),
)


# ---------------------------------------------------------------------------
# RoleModel
# ---------------------------------------------------------------------------

class RoleModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """ORM model for the ``roles`` table.

    Platform-defined roles.  The initial three roles — ``admin``,
    ``team_lead``, and ``developer`` — are seeded by a data migration and
    are immutable in this iteration of the platform.

    Roles are **global** (not tenant-scoped).  The same ``RoleModel`` row is
    referenced by all tenants via the ``user_roles`` join table.  The RBAC
    enforcement service loads all roles and their permissions at startup
    and caches the result in Redis.

    The ``is_system`` flag distinguishes platform-seeded roles (``TRUE``) from
    any future custom roles that tenant admins might create.  The application
    layer refuses to delete or rename system roles.
    """

    __tablename__ = "roles"

    # ----- Columns ----------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment=(
            "Machine-readable role identifier used in JWT claims and RBAC checks.  "
            "Examples: 'admin', 'team_lead', 'developer'."
        ),
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable role label displayed in the UI.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional prose description of the role's intended permissions.",
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment=(
            "TRUE for platform-seeded roles that cannot be deleted or renamed.  "
            "Reserved for future custom tenant roles."
        ),
    )

    # ----- Relationships ----------------------------------------------------

    permissions: Mapped[list[PermissionModel]] = relationship(
        "PermissionModel",
        secondary=role_permissions_table,
        back_populates="roles",
        lazy="raise",
    )

    user_roles: Mapped[list[UserRoleModel]] = relationship(
        "UserRoleModel",
        back_populates="role",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<RoleModel id={self.id!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# PermissionModel
# ---------------------------------------------------------------------------

class PermissionModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """ORM model for the ``permissions`` table.

    Granular permission definitions following the ``{resource}:{action}``
    naming convention (e.g., ``repository:delete``, ``analysis:trigger_full``,
    ``user:manage``).

    Permissions are **global** — they are referenced from ``role_permissions``
    and evaluated by the RBAC middleware on every authenticated request.  The
    full permission set is loaded once at startup and cached; individual
    permission records are never instantiated per-request.

    The composite ``UNIQUE (resource, action)`` constraint prevents duplicate
    permission definitions even if the ``name`` column were somehow duplicated.
    """

    __tablename__ = "permissions"

    # ----- Columns ----------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        comment=(
            "Dotted action-resource string used as the permission token in JWT claims.  "
            "Format: '{resource}:{action}'.  Example: 'repository:delete'."
        ),
    )

    resource: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment=(
            "Resource class this permission controls.  "
            "Examples: 'repository', 'analysis', 'user', 'tenant', 'agent'."
        ),
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment=(
            "Operation this permission authorises on the resource.  "
            "Examples: 'read', 'write', 'delete', 'trigger_full', 'manage'."
        ),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional prose description of what this permission grants.",
    )

    # ----- Constraints & Indexes --------------------------------------------

    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )

    # ----- Relationships ----------------------------------------------------

    roles: Mapped[list[RoleModel]] = relationship(
        "RoleModel",
        secondary=role_permissions_table,
        back_populates="permissions",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<PermissionModel id={self.id!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# UserModel
# ---------------------------------------------------------------------------

class UserModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, TenantScopedMixin, Base):
    """ORM model for the ``users`` table.

    Stores every user account across all tenants.  A user belongs to exactly
    one tenant (enforced by the non-nullable ``tenant_id`` FK).

    Authentication state
    --------------------
    - ``password_hash`` is NULL for OAuth-only users (``auth_provider != 'local'``).
    - ``auth_provider_id`` is the external OAuth subject identifier (e.g., the
      GitHub user ID or Google ``sub`` claim).  It is NULL for local-auth users.

    Account lockout
    ---------------
    After five consecutive failed login attempts (configurable via application
    logic, not a DB constraint), ``locked_until`` is set to ``now() + lockout_window``.
    The auth service checks this column before processing login attempts.

    Email uniqueness
    ----------------
    Email uniqueness is **per-tenant**, not global.  The same email address may
    be registered across different tenants.  The partial unique index on
    ``(tenant_id, email) WHERE deleted_at IS NULL`` enforces this while
    allowing soft-deleted email addresses to be re-registered.

    Tenant isolation
    ----------------
    ``TenantScopedMixin`` adds the ``tenant_id`` column and its FK to ``tenants.id``.
    The repository base class injects ``WHERE tenant_id = :tenant_id`` on every
    read, update, and delete operation against this table.
    """

    __tablename__ = "users"

    # ----- Columns ----------------------------------------------------------

    email: Mapped[str] = mapped_column(
        String(320),  # RFC 5321 max email length
        nullable=False,
        comment=(
            "User email address.  Unique within the tenant (not globally unique).  "
            "Validated to RFC 5321 format by the application layer before insert."
        ),
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Full name or nickname displayed in the UI.",
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment=(
            "bcrypt hash of the user's password.  NULL for OAuth-only accounts "
            "(auth_provider != 'local').  Never stored in plaintext."
        ),
    )

    auth_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'local'"),
        comment="Identity provider: 'local', 'github', or 'google'.",
    )

    auth_provider_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment=(
            "External OAuth subject identifier (e.g., GitHub numeric user ID or "
            "Google 'sub' claim).  NULL for local-auth users.  Indexed for OAuth "
            "callback lookups."
        ),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment=(
            "FALSE means the account is deactivated; all API calls return 401.  "
            "Distinct from soft-deletion: an inactive user still exists in the system."
        ),
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
        comment=(
            "TRUE after the user has clicked the verification link.  "
            "Unverified users may be restricted from certain operations by the "
            "auth middleware."
        ),
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="UTC instant of the most recent successful login.  NULL for new accounts.",
    )

    failed_login_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("0"),
        comment=(
            "Number of consecutive failed login attempts.  Reset to 0 on success.  "
            "Used by the auth service to trigger account lockout after 5 failures."
        ),
    )

    locked_until: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment=(
            "UTC instant until which the account is locked due to repeated login failures.  "
            "NULL means the account is not locked.  The auth service checks this before "
            "processing a login request."
        ),
    )

    # ----- Constraints & Indexes --------------------------------------------

    __table_args__ = (
        CheckConstraint(
            "auth_provider IN ('local', 'github', 'google')",
            name="ck_users_auth_provider",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_at > created_at",
            name="ck_users_deleted_at_after_created_at",
        ),
        # Partial unique index enforces per-tenant email uniqueness ONLY on
        # non-deleted rows.  A full UniqueConstraint is intentionally absent:
        # it would prevent re-registration of the same email after soft-deletion,
        # which is a documented requirement (database.md §5).  The partial index
        # is the sole enforcement mechanism for this rule.
        Index(
            "idx_users_email_tenant",
            "tenant_id",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Tenant isolation — base query filter.
        TenantScopedMixin.build_tenant_index("users", soft_deleted=True),
        # OAuth provider lookup — used during OAuth callback to find or create user.
        Index(
            "idx_users_auth_provider_id",
            "auth_provider",
            "auth_provider_id",
            postgresql_where=text("auth_provider_id IS NOT NULL"),
        ),
    )

    # ----- Relationships ----------------------------------------------------

    tenant: Mapped[Any] = relationship(  # type: ignore[type-arg]
        "TenantModel",
        back_populates="users",
        foreign_keys="UserModel.tenant_id",
        lazy="raise",
    )

    user_roles: Mapped[list[UserRoleModel]] = relationship(
        "UserRoleModel",
        back_populates="user",
        foreign_keys="UserRoleModel.user_id",
        lazy="raise",
        cascade="all, delete-orphan",
    )

    refresh_tokens: Mapped[list[RefreshTokenModel]] = relationship(
        "RefreshTokenModel",
        back_populates="user",
        foreign_keys="RefreshTokenModel.user_id",
        lazy="raise",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<UserModel id={self.id!r} "
            f"tenant_id={self.tenant_id!r} "
            f"email={self.email!r}>"
        )


# ---------------------------------------------------------------------------
# UserRoleModel
# ---------------------------------------------------------------------------

class UserRoleModel(UUIDPrimaryKeyMixin, Base):
    """ORM model for the ``user_roles`` table.

    Assigns a platform role to a user within a tenant.  The schema supports
    multiple concurrent roles per user for forward-compatibility, but the
    application enforces a single active role per user in this iteration.

    Tenant-scoped
    -------------
    A role assignment is always within a tenant context — the same user_id
    could theoretically hold different roles in different tenants.

    Active-assignment uniqueness
    ----------------------------
    The partial unique index on ``(tenant_id, user_id, role_id) WHERE revoked_at IS NULL``
    prevents duplicate active role grants without blocking the historical record
    of previous revoked assignments (audit trail).

    Granted-by
    ----------
    ``granted_by`` is the user_id of the admin who made the assignment.
    NULL for system-seeded role grants (e.g., the first admin created during
    tenant registration).
    """

    __tablename__ = "user_roles"

    # ----- Columns ----------------------------------------------------------

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
            name="fk_user_roles_tenant_id",
        ),
        nullable=False,
        comment="FK → tenants.id.  Scopes this role assignment to a single tenant.",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_user_roles_user_id",
        ),
        nullable=False,
        comment="FK → users.id.  The user receiving the role.",
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "roles.id",
            ondelete="RESTRICT",
            name="fk_user_roles_role_id",
        ),
        nullable=False,
        comment=(
            "FK → roles.id.  RESTRICT prevents deletion of a role while any "
            "assignment (including revoked historical ones) references it."
        ),
    )

    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_user_roles_granted_by",
        ),
        nullable=True,
        comment=(
            "FK → users.id of the admin who granted this role.  "
            "NULL for system-assigned roles (initial admin seed, automated provisioning)."
        ),
    )

    granted_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC instant at which this role assignment was created.",
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment=(
            "UTC instant at which this role assignment was revoked.  "
            "NULL means the assignment is currently active.  "
            "Revoked entries are retained for the audit trail."
        ),
    )

    # ----- Constraints & Indexes --------------------------------------------

    __table_args__ = (
        # Active assignment uniqueness: a user may hold each role only once
        # simultaneously within a tenant.
        Index(
            "idx_user_roles_active_assignment",
            "tenant_id",
            "user_id",
            "role_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
        # Fast lookup of a user's active roles within a tenant.
        Index(
            "idx_user_roles_user_tenant",
            "user_id",
            "tenant_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    # ----- Relationships ----------------------------------------------------

    tenant: Mapped[Any] = relationship(  # type: ignore[type-arg]
        "TenantModel",
        back_populates="user_roles",
        foreign_keys=[tenant_id],
        lazy="raise",
    )

    user: Mapped[UserModel] = relationship(
        "UserModel",
        back_populates="user_roles",
        foreign_keys=[user_id],
        lazy="raise",
    )

    role: Mapped[RoleModel] = relationship(
        "RoleModel",
        back_populates="user_roles",
        foreign_keys=[role_id],
        lazy="raise",
    )

    granted_by_user: Mapped[UserModel | None] = relationship(
        "UserModel",
        foreign_keys=[granted_by],
        lazy="raise",
    )

    def __repr__(self) -> str:
        return (
            f"<UserRoleModel id={self.id!r} "
            f"user_id={self.user_id!r} "
            f"role_id={self.role_id!r} "
            f"revoked_at={self.revoked_at!r}>"
        )


# ---------------------------------------------------------------------------
# RefreshTokenModel
# ---------------------------------------------------------------------------

class RefreshTokenModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """ORM model for the ``refresh_tokens`` table.

    Stores hashed JWT refresh tokens for token rotation.  Short-lived access
    tokens (15-minute TTL) are NOT stored in the database — they are validated
    by the JWT middleware using the signing key alone.  Refresh tokens (7-day
    TTL) are stored hashed so that token reuse can be detected and the entire
    token family can be invalidated on reuse.

    Token storage
    -------------
    ``token_hash`` is a hex-encoded SHA-256 digest of the raw refresh token
    (which is a URL-safe random 256-bit string).  The raw token is never
    stored.  The hash is unique — collision probability is negligible for
    256-bit values.

    Family-based reuse detection
    ----------------------------
    ``family_id`` is a UUID shared by all rotations of the same original
    refresh token.  When a used (already-rotated) token is presented, the
    auth service queries all tokens with the same ``family_id`` and revokes
    them all, invalidating the entire session chain.  This detects token
    theft scenarios where an attacker presents a stolen old refresh token.

    Device fingerprint
    ------------------
    ``user_agent`` and ``ip_address`` are recorded for audit and anomaly
    detection.  ``ip_address`` uses PostgreSQL's native ``INET`` type, which
    accepts both IPv4 and IPv6 without text normalisation issues.

    Tenant-scoped
    -------------
    ``tenant_id`` is explicitly declared (not via mixin) because
    ``RefreshTokenModel`` does not inherit ``TenantScopedMixin`` — doing so
    would add the mixin's ``build_tenant_index`` index, but this table uses
    a more specific partial index on ``(user_id)`` for performance on the
    hot path (token validation).  The ``tenant_id`` column and its FK are
    declared manually for full control.
    """

    __tablename__ = "refresh_tokens"

    # ----- Columns ----------------------------------------------------------

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
            name="fk_refresh_tokens_tenant_id",
        ),
        nullable=False,
        comment=(
            "FK → tenants.id.  Included for tenant-scoped revocation "
            "(e.g., 'revoke all sessions for tenant X')."
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_refresh_tokens_user_id",
        ),
        nullable=False,
        comment=(
            "FK → users.id.  CASCADE ensures all tokens are removed when a "
            "user account is hard-deleted."
        ),
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment=(
            "Hex-encoded SHA-256 digest of the raw refresh token.  "
            "The raw token is never stored.  Unique index supports O(1) lookup "
            "on token presentation."
        ),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment=(
            "UUID shared by all rotations of the same original refresh token.  "
            "Used for family-based reuse detection: when a previously-rotated "
            "token is presented, all tokens in the family are revoked."
        ),
    )

    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        comment=(
            "UTC instant after which this token is no longer valid, regardless "
            "of whether it has been revoked.  The auth service rejects tokens "
            "where expires_at <= now()."
        ),
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment=(
            "UTC instant at which this token was explicitly revoked (logout, "
            "reuse detection, or admin action).  NULL means the token is still "
            "usable (subject to expires_at)."
        ),
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment=(
            "HTTP User-Agent header from the request that issued this token.  "
            "Stored for audit and anomaly-detection purposes."
        ),
    )

    ip_address: Mapped[str | None] = mapped_column(
        INET,
        nullable=True,
        comment=(
            "Client IP address at token issuance time.  PostgreSQL INET type "
            "accepts both IPv4 and IPv6 without normalisation issues."
        ),
    )

    # ----- Constraints & Indexes --------------------------------------------

    __table_args__ = (
        # Hot-path: token validation (refresh token presentation on every
        # access-token renewal).  Partial index skips already-revoked rows,
        # which are the vast majority of all rows over time.
        #
        # NOTE: 'expires_at > now()' is intentionally ABSENT from this
        # predicate.  PostgreSQL forbids volatile functions (now(), CURRENT_
        # TIMESTAMP, etc.) in partial-index WHERE clauses — using them raises
        # "functions in index predicate must be marked IMMUTABLE".  Expiry
        # filtering is an application-layer responsibility: the auth service
        # checks 'expires_at <= now()' before accepting any token, and the
        # maintenance worker uses idx_refresh_tokens_expires_at to sweep
        # expired rows for physical deletion.
        Index(
            "idx_refresh_tokens_user",
            "user_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
        # Family-based reuse detection: fast lookup of all tokens in a family.
        Index(
            "idx_refresh_tokens_family",
            "family_id",
        ),
        # Maintenance worker sweep: clean up expired/revoked tokens.
        Index(
            "idx_refresh_tokens_expires_at",
            "expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    # ----- Relationships ----------------------------------------------------

    tenant: Mapped[Any] = relationship(  # type: ignore[type-arg]
        "TenantModel",
        back_populates="refresh_tokens",
        foreign_keys=[tenant_id],
        lazy="raise",
    )

    user: Mapped[UserModel] = relationship(
        "UserModel",
        back_populates="refresh_tokens",
        foreign_keys=[user_id],
        lazy="raise",
    )

    def __repr__(self) -> str:
        return (
            f"<RefreshTokenModel id={self.id!r} "
            f"user_id={self.user_id!r} "
            f"family_id={self.family_id!r} "
            f"revoked_at={self.revoked_at!r}>"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "role_permissions_table",
    "RoleModel",
    "PermissionModel",
    "UserModel",
    "UserRoleModel",
    "RefreshTokenModel",
]
