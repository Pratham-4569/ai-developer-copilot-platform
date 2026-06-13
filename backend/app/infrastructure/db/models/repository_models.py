"""ORM models for the Repository Management domain — Phase 3.5: Database Layer.

Tables implemented
------------------
- ``repositories``          — central metadata record for every connected
                              repository (ZIP upload or GitHub connect).
                              Raw source content lives in object storage;
                              this table holds only structural metadata and
                              lifecycle state.
- ``repository_index_runs`` — immutable history of every indexing pipeline
                              execution: trigger, type, status, chunk counts,
                              duration, and error details.

Design commitments
------------------
- Both tables carry a non-nullable ``tenant_id`` foreign key.  The
  repository base class (Phase 3.2) injects ``WHERE tenant_id = :tenant_id``
  on every read, update, and delete.  No cross-tenant access is possible at
  the infrastructure layer.

- ``repositories`` inherits ``TenantScopedMixin`` which adds the ``tenant_id``
  column with ``ondelete="RESTRICT"`` — a tenant cannot be hard-deleted while
  any repository row references it.  This is the correct production behaviour
  because the maintenance worker must purge all dependent data (index runs,
  analysis jobs, RAG chunks, Qdrant vectors) before the tenant can be removed.

- ``repository_index_runs.tenant_id`` is declared manually (not via mixin)
  with ``ondelete="CASCADE"`` so that a hard-deleted tenant removes all index
  run history automatically.  The table does not use ``TenantScopedMixin``
  because the cascade intent differs from the mixin's ``RESTRICT`` default,
  and because ``repository_index_runs`` has no ``deleted_at`` column (index
  runs are retained as an audit trail, not soft-deleted).

- ``created_by`` on ``repositories`` references ``users.id`` with
  ``ondelete="RESTRICT"`` to preserve the audit trail of who uploaded or
  connected each repository.

- ``index_status`` drives the repository lifecycle state machine:
  ``pending`` → ``indexing`` → ``ready`` (or ``error``).
  Re-index: ``ready`` → ``stale`` → ``indexing`` → ``ready``.
  The state machine is enforced by the application service layer; the
  database enforces only the allowed values via ``CHECK`` constraint.

- All ``VARCHAR`` widths follow the exact widths specified in ``database.md``
  §7.  ``JSONB`` is used only for columns explicitly typed ``JSONB`` in the
  spec (``detected_languages``, ``changed_files``).

- ``repository_index_runs.started_at`` is declared as ``NOT NULL`` with a
  server default of ``now()`` (matching the spec's ``DEFAULT now()`` note)
  because every index run record is inserted at the moment the Celery task
  picks up the job, not before.

Circular dependency risk
-------------------------
None.  FKs to ``tenants.id`` and ``users.id`` are resolved lazily by
SQLAlchemy from string-based ``ForeignKey("tablename.column")`` declarations
at DDL-emit time, not at Python import time.  No ``use_alter=True`` is
required.

References
----------
- docs/database.md — §7 "Repository Management Tables"
- docs/roadmap.md  — Phase 3 "Database Layer", Phase 5 "Repository Management"
- app/infrastructure/db/base.py — ``Base``, mixin classes
- app/infrastructure/db/models/tenant_models.py — ``TenantModel`` (FK target)
- app/infrastructure/db/models/auth_models.py   — ``UserModel`` (FK target)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
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
# RepositoryModel
# ---------------------------------------------------------------------------

class RepositoryModel(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    SoftDeleteMixin,
    TenantScopedMixin,
    Base,
):
    """ORM model for the ``repositories`` table.

    Central metadata record for every repository connected to the platform,
    whether uploaded as a ZIP archive or connected via the GitHub integration.
    Raw source content lives in object storage under ``storage_path_prefix``;
    this table holds only structural metadata and lifecycle state.

    Source types
    ------------
    - ``'zip'``    — uploaded by the user via ``POST /repositories/upload``.
    - ``'github'`` — connected via ``POST /repositories/connect/github``.

    Index status lifecycle
    ----------------------
    ::

        pending → indexing → ready
                      ↘
                       error  (retrigger via POST /repositories/{id}/reindex)
        stale → indexing → ready

    ``pending``   — initial state on insert; Celery task enqueued but not
                    picked up.
    ``indexing``  — Celery ``index_repository`` task is executing.
    ``ready``     — pipeline completed; Qdrant collection populated;
                    ``last_indexed_at`` set.
    ``error``     — pipeline failed after all retries; ``index_error_message``
                    contains the last exception detail.
    ``stale``     — repository content has changed (GitHub push) and a
                    re-index has been enqueued but not yet started.

    Soft deletion
    -------------
    ``deleted_at IS NOT NULL`` hides the repository from all listing queries.
    The ``RepositoryDeletionWorker`` Celery task runs asynchronously to purge
    the Qdrant collection and all dependent database rows before the
    maintenance worker performs the final hard delete.

    ``idx_repositories_deleted`` is a partial index on ``(deleted_at) WHERE
    deleted_at IS NOT NULL`` to support the cleanup worker's sweep query.

    Tenant isolation
    ----------------
    ``TenantScopedMixin`` adds the ``tenant_id`` column with
    ``ondelete="RESTRICT"``.  The repository base class injects
    ``WHERE tenant_id = :tenant_id`` on every query.

    Relationships
    -------------
    ``index_runs`` — one-to-many to :class:`RepositoryIndexRunModel`.
    """

    __tablename__ = "repositories"

    # ----- Columns ----------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable repository name displayed in the UI.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional repository description provided by the user.",
    )

    source_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Ingestion method: 'zip' (manual upload) or 'github' (GitHub integration).",
    )

    primary_language: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment=(
            "Dominant programming language detected during indexing.  "
            "NULL until the first indexing run completes."
        ),
    )

    detected_languages: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "JSON array of all programming languages detected in the repository.  "
            "Example: [\"Python\", \"TypeScript\", \"Dockerfile\"].  "
            "NULL until the first indexing run completes."
        ),
    )

    index_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'pending'"),
        comment=(
            "Current lifecycle state of the indexing pipeline.  "
            "Allowed values: 'pending', 'indexing', 'ready', 'error', 'stale'.  "
            "Managed by the ingestion service; the CHECK constraint enforces the "
            "allowed set at the schema level."
        ),
    )

    index_error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Last exception message from a failed indexing run.  "
            "NULL when index_status is not 'error'.  "
            "Overwritten on each failure."
        ),
    )

    last_indexed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment=(
            "UTC instant at which the most recent successful indexing run completed.  "
            "NULL until the first successful run.  "
            "Used to compute index staleness."
        ),
    )

    last_analysis_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment=(
            "UTC instant at which the most recent analysis job completed for this "
            "repository.  NULL until the first analysis job completes.  "
            "Displayed in the Repository Dashboard."
        ),
    )

    total_files: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of source files processed in the last successful indexing run.",
    )

    total_lines_of_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Approximate total lines of code across all non-binary, non-vendor files.  "
            "Computed during indexing; NULL until first successful run."
        ),
    )

    total_chunks: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Number of vector points currently stored in the Qdrant collection for "
            "this repository.  Updated at the end of each successful indexing run.  "
            "NULL until first successful run."
        ),
    )

    storage_path_prefix: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment=(
            "Object storage path prefix for all artifacts belonging to this repository.  "
            "Convention: '{tenant_id}/{repository_id}/'.  "
            "Set on creation; never changed."
        ),
    )

    default_branch: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment=(
            "Default branch name for GitHub-sourced repositories (e.g., 'main', 'master').  "
            "NULL for ZIP-uploaded repositories."
        ),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment=(
            "FALSE means the repository is administratively disabled.  "
            "Distinct from soft-deletion: an inactive repository still exists "
            "but is excluded from analysis scheduling and chat scoping."
        ),
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
            name="fk_repositories_created_by",
        ),
        nullable=False,
        comment=(
            "FK → users.id of the user who uploaded or connected this repository.  "
            "RESTRICT preserves the audit record even after the user is soft-deleted.  "
            "NOT NULL — every repository must have a known creator."
        ),
    )

    # ----- Constraints & Indexes --------------------------------------------

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('zip', 'github')",
            name="ck_repositories_source_type",
        ),
        CheckConstraint(
            "index_status IN ('pending', 'indexing', 'ready', 'error', 'stale')",
            name="ck_repositories_index_status",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_at > created_at",
            name="ck_repositories_deleted_at_after_created_at",
        ),
        # Tenant isolation — mandatory base query filter.
        # Partial: skips soft-deleted repositories (which are excluded from all
        # normal repository queries anyway).
        TenantScopedMixin.build_tenant_index("repositories", soft_deleted=True),
        # Composite: tenant + index_status.  Used by the indexing status
        # dashboard and the analysis scheduling service to find
        # repositories in a given state for a tenant.
        Index(
            "idx_repositories_tenant_status",
            "tenant_id",
            "index_status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Cleanup worker sweep: find all soft-deleted repositories that still
        # require async purging (Qdrant deletion, dependent row cleanup).
        # Partial index restricts to non-NULL deleted_at rows only.
        Index(
            "idx_repositories_deleted",
            "deleted_at",
            postgresql_where=text("deleted_at IS NOT NULL"),
        ),
    )

    # ----- Relationships ----------------------------------------------------

    index_runs: Mapped[list[RepositoryIndexRunModel]] = relationship(
        "RepositoryIndexRunModel",
        back_populates="repository",
        lazy="raise",
        cascade="all, delete-orphan",
    )

    created_by_user: Mapped[Any] = relationship(
        "UserModel",
        foreign_keys=[created_by],
        lazy="raise",
    )

    def __repr__(self) -> str:
        return (
            f"<RepositoryModel id={self.id!r} "
            f"tenant_id={self.tenant_id!r} "
            f"name={self.name!r} "
            f"index_status={self.index_status!r}>"
        )


# ---------------------------------------------------------------------------
# RepositoryIndexRunModel
# ---------------------------------------------------------------------------

class RepositoryIndexRunModel(UUIDPrimaryKeyMixin, Base):
    """ORM model for the ``repository_index_runs`` table.

    Immutable history of every indexing pipeline execution for a repository.
    One row is inserted when the Celery ``index_repository`` task begins; its
    ``status``, ``completed_at``, and chunk-count columns are updated when
    the task finishes (successfully or not).

    This table provides:
    - Full audit trail of all index runs (trigger, type, duration, outcome).
    - Diagnosis data for indexing failures (``error_message``).
    - Chunk-level statistics for freshness and capacity monitoring.
    - Celery task tracking via ``celery_task_id``.
    - Incremental re-index state via ``changed_files`` (JSONB list of paths).

    Tenant isolation
    ----------------
    ``tenant_id`` is declared manually (not via ``TenantScopedMixin``) with
    ``ondelete="CASCADE"``.  This differs from the ``RESTRICT`` default in the
    mixin — cascade is correct here because index run history should be
    removed automatically if the tenant is hard-deleted (after repository
    purge) without requiring an explicit sweep.

    Index run records are **not** soft-deleted.  They are retained for the
    duration defined by ``tenant_settings.analysis_retention_days`` and then
    hard-deleted by the maintenance worker.

    Relationships
    -------------
    ``repository`` — many-to-one to :class:`RepositoryModel`.
    """

    __tablename__ = "repository_index_runs"

    # ----- Columns ----------------------------------------------------------

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
            name="fk_index_runs_tenant_id",
        ),
        nullable=False,
        comment=(
            "FK → tenants.id.  CASCADE: index run history is automatically removed "
            "when the tenant is hard-deleted after repository purge."
        ),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "repositories.id",
            ondelete="CASCADE",
            name="fk_index_runs_repository_id",
        ),
        nullable=False,
        comment=(
            "FK → repositories.id.  CASCADE: all index run records are removed "
            "when the parent repository is hard-deleted by the maintenance worker."
        ),
    )

    trigger: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment=(
            "What initiated this index run.  "
            "Allowed values: 'manual' (user-triggered via POST /reindex), "
            "'github_push' (webhook event), 'initial' (first index after upload "
            "or GitHub connect), 'scheduled' (Celery Beat periodic re-index)."
        ),
    )

    index_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment=(
            "Scope of the indexing run.  "
            "'full' reprocesses every file in the repository.  "
            "'incremental' processes only files changed since the last run "
            "(diff list stored in changed_files)."
        ),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'running'"),
        comment=(
            "Current execution state.  "
            "Allowed values: 'running', 'completed', 'failed', 'cancelled'.  "
            "Set to 'running' on insert; updated by the Celery task on completion."
        ),
    )

    started_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=text("now()"),
        comment=(
            "UTC instant at which the Celery task picked up this run.  "
            "Set on insert; never updated."
        ),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment=(
            "UTC instant at which the indexing run finished (successfully or not).  "
            "NULL while status is 'running'."
        ),
    )

    files_processed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Number of source files that were read, parsed, and submitted for "
            "chunking in this run.  NULL until the run completes."
        ),
    )

    files_skipped: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Number of files excluded by the normalisation filter (binaries, "
            "vendor directories, build artifacts, etc.).  NULL until run completes."
        ),
    )

    chunks_created: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Number of new vector points inserted into the Qdrant collection.  "
            "NULL until the run completes."
        ),
    )

    chunks_updated: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Number of existing vector points updated (content changed).  "
            "Relevant for incremental runs only.  NULL until the run completes."
        ),
    )

    chunks_deleted: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Number of vector points removed because their source files were "
            "deleted or excluded.  Relevant for incremental runs.  NULL until "
            "the run completes."
        ),
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Exception message and traceback from the last failure in this run.  "
            "NULL when status is 'completed' or 'cancelled'."
        ),
    )

    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment=(
            "Celery task UUID for the ``index_repository`` task backing this run.  "
            "Allows the API layer to query Celery for live task status via "
            "``AsyncResult(celery_task_id)``.  NULL for cancelled or manually "
            "inserted runs."
        ),
    )

    git_commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        comment=(
            "SHA-1 of the HEAD commit at the time of this index run.  "
            "NULL for ZIP uploads (no git history) and for incremental runs "
            "on non-git sources."
        ),
    )

    changed_files: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "JSON array of repository-relative file paths that were changed since "
            "the previous index run.  Populated only for incremental runs; NULL "
            "for full runs.  Used by the ingestion pipeline to limit reprocessing."
        ),
    )

    # ----- Constraints & Indexes --------------------------------------------

    __table_args__ = (
        CheckConstraint(
            "trigger IN ('manual', 'github_push', 'initial', 'scheduled')",
            name="ck_index_runs_trigger",
        ),
        CheckConstraint(
            "index_type IN ('full', 'incremental')",
            name="ck_index_runs_index_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name="ck_index_runs_status",
        ),
        # Primary access pattern: fetch all index runs for a repository,
        # ordered most-recent-first.  Used by GET /repositories/{id}/index-runs.
        Index(
            "idx_index_runs_repo",
            "repository_id",
            "started_at",
            postgresql_ops={"started_at": "DESC"},
        ),
        # Used by the ingestion status monitor to find in-flight runs across
        # all repositories for a tenant (alerting on long-running tasks).
        Index(
            "idx_index_runs_tenant_status",
            "tenant_id",
            "status",
            postgresql_where=text("status = 'running'"),
        ),
        # Used by the API layer to resolve a Celery task ID back to an index
        # run record for live progress polling.
        Index(
            "idx_index_runs_celery",
            "celery_task_id",
            postgresql_where=text("celery_task_id IS NOT NULL"),
        ),
    )

    # ----- Relationships ----------------------------------------------------

    repository: Mapped[RepositoryModel] = relationship(
        "RepositoryModel",
        back_populates="index_runs",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return (
            f"<RepositoryIndexRunModel id={self.id!r} "
            f"repository_id={self.repository_id!r} "
            f"trigger={self.trigger!r} "
            f"status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "RepositoryModel",
    "RepositoryIndexRunModel",
]
