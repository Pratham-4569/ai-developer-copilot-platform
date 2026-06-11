"""Alembic async migration environment."""

from logging.config import fileConfig

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # Wired in Phase 3: Database Layer


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option('sqlalchemy.url')
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    raise NotImplementedError('Async migration runner wired in Phase 3')


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

