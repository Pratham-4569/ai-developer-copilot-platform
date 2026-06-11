"""Application configuration via Pydantic BaseSettings.

All secrets (API keys, passwords, signing keys) have no default values and
must be supplied at runtime via environment variables or a .env file. Non-secret
tunables carry safe defaults. Call ``get_settings.cache_clear()`` in tests before
overriding settings.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = 'AI Developer Copilot Platform'
    app_env: str = 'development'
    api_v1_prefix: str = '/api/v1'

    # -------------------------------------------------------------------------
    # Database
    # APPLICATION path: routes through PgBouncer (transaction pooling mode).
    # asyncpg prepared-statement cache is disabled for PgBouncer compatibility.
    # -------------------------------------------------------------------------
    database_url: str

    # MIGRATION path: direct connection to PostgreSQL — used by Alembic only.
    # PgBouncer transaction mode is incompatible with advisory locks and DDL
    # statements issued by Alembic. Keep this pointing at postgres:5432 directly.
    database_direct_url: str

    # -------------------------------------------------------------------------
    # Redis — Celery broker/result backend, cache, rate limiting, sessions
    # -------------------------------------------------------------------------
    redis_url: str

    # -------------------------------------------------------------------------
    # Celery — task queue
    # -------------------------------------------------------------------------
    celery_broker_url: str
    celery_result_backend: str

    # -------------------------------------------------------------------------
    # Qdrant — vector store
    # -------------------------------------------------------------------------
    qdrant_url: str
    qdrant_api_key: str | None = None  # Optional; required for authenticated clusters

    # -------------------------------------------------------------------------
    # Object Storage — S3-compatible (MinIO in dev, AWS S3 / GCS in production)
    # -------------------------------------------------------------------------
    object_storage_endpoint_url: str
    object_storage_bucket: str
    object_storage_access_key: str
    object_storage_secret_key: str
    object_storage_region: str = 'us-east-1'

    # -------------------------------------------------------------------------
    # LLM Provider — OpenAI-compatible /v1/chat/completions
    # Switch provider by changing LLM_BASE_URL:
    #   OpenAI:      https://api.openai.com
    #   Azure OAI:   https://<resource>.openai.azure.com
    #   Groq:        https://api.groq.com/openai
    #   Ollama:      http://localhost:11434
    # -------------------------------------------------------------------------
    llm_base_url: str
    llm_api_key: str
    llm_model: str = 'gpt-4o'
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 3

    # -------------------------------------------------------------------------
    # Embedding Provider — OpenAI-compatible /v1/embeddings
    # May point at the same endpoint as LLM_BASE_URL or a separate service.
    # -------------------------------------------------------------------------
    embedding_base_url: str
    embedding_api_key: str
    embedding_model: str = 'text-embedding-3-large'
    embedding_batch_size: int = 512

    # -------------------------------------------------------------------------
    # JWT
    # -------------------------------------------------------------------------
    jwt_secret_key: str
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application settings singleton.

    Cached after the first call. In unit tests, call
    ``get_settings.cache_clear()`` before patching env vars.
    """
    return Settings()

