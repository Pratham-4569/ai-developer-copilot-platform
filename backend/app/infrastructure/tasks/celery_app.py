"""Celery application factory.

Defines the ``celery_app`` singleton used by all worker processes and the
FastAPI app (for dispatching tasks via ``.delay()`` and ``.apply_async()``).

Queue layout (one dedicated worker pool per queue):
    indexing_queue  — repository ingestion and re-indexing (Phase 6)
    analysis_queue  — analysis orchestration (Phases 10+)
    agent_queue     — individual LangGraph agent execution (Phases 11–18)

All queues share the same Redis broker (database 1) and result backend
(database 2) configured in Settings. Separate Redis databases prevent
result records from polluting the broker stream.

Idempotency configuration:
    task_acks_late=True           — task is acknowledged AFTER execution,
                                    not on delivery. On worker crash the
                                    task is re-queued automatically.
    task_reject_on_worker_lost=True — explicit re-queue on SIGKILL/OOM.
    worker_prefetch_multiplier=1  — workers pull one task at a time to
                                    prevent a slow task from blocking others
                                    from being picked up on sibling queues.

Security:
    task_serializer='json'        — pickle is disabled; only JSON payloads
                                    are accepted or produced.
"""

from celery import Celery

from app.config import get_settings


def create_celery_app() -> Celery:
    """Create and configure the Celery application.

    Returns:
        A fully configured :class:`Celery` instance.
    """
    settings = get_settings()

    app = Celery('ai_copilot')

    app.conf.update(
        # ------------------------------------------------------------------
        # Broker and result backend
        # ------------------------------------------------------------------
        broker_url=settings.celery_broker_url,
        result_backend=settings.celery_result_backend,

        # ------------------------------------------------------------------
        # Serialization — JSON only; pickle is disabled for security
        # ------------------------------------------------------------------
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        event_serializer='json',

        # ------------------------------------------------------------------
        # Timezone
        # ------------------------------------------------------------------
        timezone='UTC',
        enable_utc=True,

        # ------------------------------------------------------------------
        # Queue routing — tasks are routed by module path prefix
        # ------------------------------------------------------------------
        task_routes={
            'app.infrastructure.tasks.indexing_tasks.*': {'queue': 'indexing_queue'},
            'app.infrastructure.tasks.analysis_tasks.*': {'queue': 'analysis_queue'},
            'app.infrastructure.tasks.agent_tasks.*':    {'queue': 'agent_queue'},
            'app.infrastructure.tasks.github_tasks.*':   {'queue': 'indexing_queue'},
            'app.infrastructure.tasks.maintenance_tasks.*': {'queue': 'analysis_queue'},
        },

        # ------------------------------------------------------------------
        # Idempotency and reliability
        # ------------------------------------------------------------------
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_track_started=True,      # Exposes STARTED state for monitoring

        # One task at a time per worker process — prevents a long-running
        # indexing task from blocking analysis tasks on the same process.
        worker_prefetch_multiplier=1,

        # ------------------------------------------------------------------
        # Result expiry — keep results for 24 hours then discard
        # ------------------------------------------------------------------
        result_expires=86_400,

        # ------------------------------------------------------------------
        # Beat schedule — populated incrementally per phase
        # ------------------------------------------------------------------
        beat_schedule={},
    )

    # Auto-discover task modules so that ``@celery_app.task`` decorators in
    # each module register correctly on both worker startup and API import.
    app.autodiscover_tasks([
        'app.infrastructure.tasks.indexing_tasks',
        'app.infrastructure.tasks.analysis_tasks',
        'app.infrastructure.tasks.agent_tasks',
        'app.infrastructure.tasks.github_tasks',
        'app.infrastructure.tasks.maintenance_tasks',
    ])

    return app


# ---------------------------------------------------------------------------
# Module-level singleton.
# Celery requires that the app object exists at import time of the module
# referenced by ``-A app.infrastructure.tasks.celery_app``. All task modules
# import ``celery_app`` from here to decorate their task functions.
# ---------------------------------------------------------------------------
celery_app = create_celery_app()
