"""Application configuration via Pydantic BaseSettings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'AI Developer Copilot Platform'
    app_env: str = 'development'
    api_v1_prefix: str = '/api/v1'
    database_url: str
    redis_url: str
    qdrant_url: str
    jwt_secret_key: str
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()

