"""Phase 1 scaffold generator for AI-Powered Developer Copilot Platform."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(r"d:\AI Developer Copilot Platform")
DOCS_SRC = Path(r"C:\Users\kalep\Downloads")

# All directories per scaffold.md
DIRS = [
    "docs",
    "backend/alembic/versions",
    "backend/tests/unit/domain",
    "backend/tests/unit/application",
    "backend/tests/unit/agents",
    "backend/tests/integration/repositories",
    "backend/tests/integration/services",
    "backend/tests/integration/agents",
    "backend/tests/e2e/auth",
    "backend/tests/e2e/repositories",
    "backend/tests/e2e/chat",
    "backend/tests/e2e/analysis",
    "backend/app/domain/entities",
    "backend/app/domain/value_objects",
    "backend/app/domain/events",
    "backend/app/domain/interfaces",
    "backend/app/application/auth",
    "backend/app/application/tenant",
    "backend/app/application/repository",
    "backend/app/application/indexing",
    "backend/app/application/rag",
    "backend/app/application/chat",
    "backend/app/application/analysis",
    "backend/app/application/agents",
    "backend/app/application/github",
    "backend/app/application/dashboard",
    "backend/app/application/audit",
    "backend/app/infrastructure/db/models",
    "backend/app/infrastructure/db/repositories",
    "backend/app/infrastructure/vector",
    "backend/app/infrastructure/cache",
    "backend/app/infrastructure/storage",
    "backend/app/infrastructure/llm",
    "backend/app/infrastructure/github",
    "backend/app/infrastructure/events",
    "backend/app/infrastructure/tasks",
    "backend/app/interfaces/api/v1",
    "backend/app/interfaces/webhooks",
    "backend/app/interfaces/schemas",
    "backend/app/interfaces/middleware",
    "backend/app/agents/base",
    "backend/app/agents/shared",
    "backend/app/agents/orchestration",
    "backend/app/agents/architecture",
    "backend/app/agents/code_review",
    "backend/app/agents/bug_detection",
    "backend/app/agents/security",
    "backend/app/agents/documentation",
    "backend/app/agents/test_generation",
    "backend/app/agents/issue_generation",
    "backend/app/agents/refactoring",
    "frontend/src/router/guards",
    "frontend/src/router/routes",
    "frontend/src/stores",
    "frontend/src/api",
    "frontend/src/types",
    "frontend/src/composables",
    "frontend/src/modules/auth/views",
    "frontend/src/modules/auth/components",
    "frontend/src/modules/repository/views",
    "frontend/src/modules/repository/components",
    "frontend/src/modules/chat/views",
    "frontend/src/modules/chat/components",
    "frontend/src/modules/analysis/views",
    "frontend/src/modules/analysis/components",
    "frontend/src/modules/dashboard/views",
    "frontend/src/modules/dashboard/components",
    "frontend/src/modules/settings/views",
    "frontend/src/modules/settings/components",
    "frontend/src/shared/components",
    "frontend/src/shared/icons",
    "docker/nginx/conf.d",
    "infrastructure/k8s/namespaces",
    "infrastructure/k8s/deployments",
    "infrastructure/k8s/services",
    "infrastructure/k8s/configmaps",
    "infrastructure/k8s/hpa",
    "infrastructure/k8s/ingress",
    "infrastructure/helm/ai-copilot/templates",
    "infrastructure/terraform/modules/networking",
    "infrastructure/terraform/modules/database",
    "infrastructure/terraform/modules/redis",
    "infrastructure/terraform/modules/qdrant",
    "infrastructure/terraform/modules/storage",
    "infrastructure/terraform/modules/container_registry",
    "infrastructure/terraform/modules/secrets",
    "infrastructure/terraform/envs/staging",
    "infrastructure/terraform/envs/production",
    "infrastructure/monitoring/prometheus/rules",
    "infrastructure/monitoring/grafana/datasources",
    "infrastructure/monitoring/grafana/dashboards",
    "infrastructure/monitoring/loki",
    ".github/workflows",
]

INIT_PACKAGES = [
    "backend/app",
    "backend/app/domain",
    "backend/app/domain/entities",
    "backend/app/domain/value_objects",
    "backend/app/domain/events",
    "backend/app/domain/interfaces",
    "backend/app/application",
    "backend/app/application/auth",
    "backend/app/application/tenant",
    "backend/app/application/repository",
    "backend/app/application/indexing",
    "backend/app/application/rag",
    "backend/app/application/chat",
    "backend/app/application/analysis",
    "backend/app/application/agents",
    "backend/app/application/github",
    "backend/app/application/dashboard",
    "backend/app/application/audit",
    "backend/app/infrastructure",
    "backend/app/infrastructure/db",
    "backend/app/infrastructure/db/models",
    "backend/app/infrastructure/db/repositories",
    "backend/app/infrastructure/vector",
    "backend/app/infrastructure/cache",
    "backend/app/infrastructure/storage",
    "backend/app/infrastructure/llm",
    "backend/app/infrastructure/github",
    "backend/app/infrastructure/events",
    "backend/app/infrastructure/tasks",
    "backend/app/interfaces",
    "backend/app/interfaces/api",
    "backend/app/interfaces/api/v1",
    "backend/app/interfaces/webhooks",
    "backend/app/interfaces/schemas",
    "backend/app/interfaces/middleware",
    "backend/app/agents",
    "backend/app/agents/base",
    "backend/app/agents/shared",
    "backend/app/agents/orchestration",
    "backend/app/agents/architecture",
    "backend/app/agents/code_review",
    "backend/app/agents/bug_detection",
    "backend/app/agents/security",
    "backend/app/agents/documentation",
    "backend/app/agents/test_generation",
    "backend/app/agents/issue_generation",
    "backend/app/agents/refactoring",
]

PY_STUBS: dict[str, str] = {}


def py_module(doc: str, body: str = "") -> str:
    return f'"""{doc}"""\n\n{body}\n'


def ensure_dirs() -> None:
    for d in DIRS:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    for pkg in INIT_PACKAGES:
        init = ROOT / pkg / "__init__.py"
        if not init.exists():
            init.write_text(f'"""Package: {pkg.replace("backend/app/", "")}."""\n', encoding="utf-8")


def copy_docs() -> None:
    for name in [
        "constitution.md",
        "llm_contract.md",
        "scaffold.md",
        "architecture.md",
        "roadmap.md",
        "api.md",
        "database.md",
        "prd.md",
    ]:
        src = DOCS_SRC / name
        if src.exists():
            shutil.copy2(src, ROOT / "docs" / name)


def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_python_stubs() -> None:
    domain_entities = [
        "tenant",
        "user",
        "repository",
        "analysis_job",
        "agent_finding",
        "agent_run",
        "chat_session",
        "chat_message",
        "rag_chunk",
    ]
    for name in domain_entities:
        write(
            f"backend/app/domain/entities/{name}.py",
            py_module(f"Domain entity: {name.replace('_', ' ')}."),
        )

    value_objects = [
        "tenant_id",
        "repository_id",
        "severity",
        "analysis_scope",
        "agent_type",
        "index_status",
        "job_status",
        "confidence_score",
    ]
    for name in value_objects:
        write(
            f"backend/app/domain/value_objects/{name}.py",
            py_module(f"Value object: {name.replace('_', ' ')}."),
        )

    events = {
        "base_event.py": "Base domain event.",
        "repository_events.py": "Repository domain events.",
        "analysis_events.py": "Analysis domain events.",
        "github_events.py": "GitHub domain events.",
    }
    for fname, doc in events.items():
        write(f"backend/app/domain/events/{fname}", py_module(doc))

    interfaces = [
        "tenant_repository",
        "user_repository",
        "repository_repository",
        "analysis_repository",
        "agent_run_repository",
        "finding_repository",
        "chat_repository",
        "rag_chunk_repository",
        "audit_repository",
        "event_outbox_repository",
    ]
    for name in interfaces:
        cls = "I" + "".join(p.capitalize() for p in name.split("_"))
        write(
            f"backend/app/domain/interfaces/{name}.py",
            py_module(
                f"Repository interface: {cls}.",
                "from abc import ABC, abstractmethod\n\n\n"
                f"class {cls}(ABC):\n"
                '    """Abstract repository contract."""\n',
            ),
        )

    app_services = {
        "auth/auth_service.py": "Authentication use cases.",
        "auth/rbac_service.py": "RBAC permission resolution.",
        "auth/token_service.py": "JWT token lifecycle.",
        "tenant/tenant_service.py": "Tenant lifecycle use cases.",
        "tenant/tenant_context.py": "Tenant context propagation.",
        "repository/repository_service.py": "Repository management use cases.",
        "repository/ingestion_service.py": "Repository ingestion orchestration.",
        "indexing/indexing_service.py": "Indexing orchestration.",
        "indexing/chunking_service.py": "Language-aware chunking.",
        "indexing/file_filter_service.py": "File filtering for indexing.",
        "rag/rag_service.py": "RAG retrieval use cases.",
        "rag/embedding_service.py": "Embedding orchestration.",
        "rag/citation_service.py": "Citation assembly.",
        "chat/chat_service.py": "Chat message handling.",
        "chat/session_service.py": "Chat session management.",
        "chat/scope_resolver.py": "Chat scope resolution.",
        "analysis/analysis_orchestration_service.py": "Analysis job orchestration.",
        "analysis/finding_service.py": "Finding management.",
        "agents/agent_orchestration_service.py": "Agent dispatch orchestration.",
        "github/github_integration_service.py": "GitHub integration use cases.",
        "github/pr_review_service.py": "PR review orchestration.",
        "dashboard/dashboard_service.py": "Dashboard analytics queries.",
        "audit/audit_service.py": "Structured audit logging.",
    }
    for path, doc in app_services.items():
        write(f"backend/app/application/{path}", py_module(doc))

    infra_db = {
        "db/session.py": "Async SQLAlchemy session factory.",
        "db/base.py": "SQLAlchemy declarative base.",
    }
    for path, doc in infra_db.items():
        write(f"backend/app/infrastructure/{path}", py_module(doc))

    orm_models = [
        "auth_models",
        "tenant_models",
        "repository_models",
        "analysis_models",
        "rag_models",
        "chat_models",
        "github_models",
        "dashboard_models",
        "audit_models",
    ]
    for name in orm_models:
        write(
            f"backend/app/infrastructure/db/models/{name}.py",
            py_module(f"ORM models: {name.replace('_', ' ')}."),
        )

    repo_impls = [
        "tenant_repository",
        "user_repository",
        "repository_repository",
        "analysis_repository",
        "agent_run_repository",
        "finding_repository",
        "chat_repository",
        "audit_repository",
        "event_outbox_repository",
    ]
    for name in repo_impls:
        write(
            f"backend/app/infrastructure/db/repositories/{name}.py",
            py_module(f"SQLAlchemy repository: {name}."),
        )

    infra_other = {
        "vector/qdrant_client.py": "Qdrant async client factory.",
        "vector/qdrant_chunk_repository.py": "IRAGChunkRepository implementation.",
        "cache/redis_client.py": "Redis async client factory.",
        "cache/cache_adapter.py": "Redis cache adapter.",
        "storage/object_storage_adapter.py": "S3-compatible object storage adapter.",
        "llm/llm_adapter.py": "LLM provider adapter.",
        "llm/embedding_adapter.py": "Embedding provider adapter.",
        "github/github_api_adapter.py": "GitHub REST API adapter.",
        "github/github_app_auth.py": "GitHub App authentication.",
        "events/event_publisher.py": "Transactional outbox event publisher.",
        "tasks/celery_app.py": "Celery application factory.",
        "tasks/celery_beat_schedule.py": "Celery Beat schedule.",
        "tasks/indexing_tasks.py": "Indexing Celery tasks.",
        "tasks/analysis_tasks.py": "Analysis Celery tasks.",
        "tasks/agent_tasks.py": "Agent Celery tasks.",
        "tasks/github_tasks.py": "GitHub Celery tasks.",
        "tasks/maintenance_tasks.py": "Maintenance Celery tasks.",
    }
    for path, doc in infra_other.items():
        write(f"backend/app/infrastructure/{path}", py_module(doc))

    api_routes = [
        "router",
        "auth",
        "tenants",
        "repositories",
        "analysis",
        "agents",
        "chat",
        "rag",
        "github",
        "dashboard",
    ]
    for name in api_routes:
        write(f"backend/app/interfaces/api/v1/{name}.py", py_module(f"API v1 routes: {name}."))

    write("backend/app/interfaces/webhooks/github_webhook.py", py_module("GitHub webhook receiver."))

    schemas = [
        "auth_schemas",
        "tenant_schemas",
        "repository_schemas",
        "analysis_schemas",
        "agent_schemas",
        "finding_schemas",
        "chat_schemas",
        "rag_schemas",
        "github_schemas",
        "dashboard_schemas",
        "common_schemas",
    ]
    for name in schemas:
        write(f"backend/app/interfaces/schemas/{name}.py", py_module(f"Pydantic schemas: {name}."))

    middleware = [
        "auth_middleware",
        "tenant_middleware",
        "rbac_middleware",
        "audit_middleware",
        "rate_limit_middleware",
        "request_logging_middleware",
    ]
    for name in middleware:
        write(f"backend/app/interfaces/middleware/{name}.py", py_module(f"Middleware: {name}."))

    agent_base = {
        "base/base_agent.py": "Abstract LangGraph agent base class.",
        "base/agent_state.py": "Shared AgentState TypedDict.",
        "base/agent_config.py": "AgentConfig dataclass.",
        "base/agent_nodes.py": "Shared LangGraph nodes.",
        "base/agent_output.py": "AgentOutput Pydantic model.",
        "base/agent_exceptions.py": "Agent-specific exceptions.",
        "shared/prompt_library.py": "Agent system prompts.",
        "shared/retrieval_profiles.py": "Per-agent retrieval profiles.",
        "shared/finding_schema.py": "Canonical AgentFinding schema.",
        "shared/severity_classifier.py": "Severity scoring.",
        "shared/output_formatter.py": "Finding serialization.",
        "orchestration/orchestrator.py": "Celery group dispatch.",
        "orchestration/scope_resolver.py": "Analysis scope resolution.",
        "orchestration/result_aggregator.py": "Finding aggregation.",
    }
    for path, doc in agent_base.items():
        write(f"backend/app/agents/{path}", py_module(doc))

    agents = [
        "architecture",
        "code_review",
        "bug_detection",
        "security",
        "documentation",
        "test_generation",
        "issue_generation",
        "refactoring",
    ]
    for agent in agents:
        for suffix in ["agent", "planner", "reasoner", "output"]:
            write(
                f"backend/app/agents/{agent}/{agent}_{suffix}.py",
                py_module(f"{agent.replace('_', ' ').title()} {suffix.replace('_', ' ')}."),
            )

    write(
        "backend/app/main.py",
        py_module(
            "FastAPI application factory.",
            "from fastapi import FastAPI\n\n\n"
            "def create_app() -> FastAPI:\n"
            '    """Create and configure the FastAPI application."""\n'
            "    app = FastAPI(title='AI Developer Copilot Platform', version='1.0.0')\n"
            "    return app\n\n\n"
            "app = create_app()\n",
        ),
    )
    write(
        "backend/app/config.py",
        py_module(
            "Application configuration via Pydantic BaseSettings.",
            "from pydantic_settings import BaseSettings, SettingsConfigDict\n\n\n"
            "class Settings(BaseSettings):\n"
            '    """Environment-driven application settings."""\n\n'
            "    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')\n\n"
            "    app_name: str = 'AI Developer Copilot Platform'\n"
            "    app_env: str = 'development'\n"
            "    api_v1_prefix: str = '/api/v1'\n"
            "    database_url: str\n"
            "    redis_url: str\n"
            "    qdrant_url: str\n"
            "    jwt_secret_key: str\n"
            "    jwt_algorithm: str = 'HS256'\n"
            "    access_token_expire_minutes: int = 15\n"
            "    refresh_token_expire_days: int = 7\n\n\n"
            "def get_settings() -> Settings:\n"
            '    """Return cached settings instance."""\n'
            "    return Settings()\n",
        ),
    )
    write(
        "backend/app/dependencies.py",
        py_module(
            "FastAPI dependency injection wiring.",
            "# DI wiring: bridge application services and infrastructure implementations.\n",
        ),
    )
    write(
        "backend/tests/conftest.py",
        py_module("Shared pytest fixtures."),
    )
    for sub in [
        "unit/domain/.gitkeep",
        "unit/application/.gitkeep",
        "unit/agents/.gitkeep",
        "integration/repositories/.gitkeep",
        "integration/services/.gitkeep",
        "integration/agents/.gitkeep",
        "e2e/auth/.gitkeep",
        "e2e/repositories/.gitkeep",
        "e2e/chat/.gitkeep",
        "e2e/analysis/.gitkeep",
    ]:
        write(f"backend/tests/{sub}", "")


def build_root_files() -> None:
    write(
        ".gitignore",
        """# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.mypy_cache/
.ruff_cache/
.pytest_cache/
htmlcov/
.coverage

# Node
node_modules/
dist/
*.local

# Environment
.env
.env.local
.env.*.local
!.env.example

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Build
*.log
""",
    )
    write(
        "README.md",
        """# AI-Powered Developer Copilot Platform

Production-grade, multi-tenant SaaS platform for repository-aware AI engineering assistance.

## Monorepo Structure

- `backend/` — FastAPI application (Clean Architecture)
- `frontend/` — Vue 3 SPA
- `infrastructure/` — Kubernetes, Helm, Terraform, monitoring
- `docker/` — Docker Compose and NGINX configuration
- `docs/` — Canonical project documentation

## Phase 1 Status

This repository contains the Phase 1 project scaffold only. Business logic and feature implementations follow the roadmap in `docs/roadmap.md`.

## Documentation

See `docs/scaffold.md` for the canonical repository structure reference.

## Local Development

```bash
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
```

## License

Proprietary — Internal use only.
""",
    )
    write(
        ".pre-commit-config.yaml",
        """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        files: ^backend/
        additional_dependencies: [pydantic, pydantic-settings, fastapi]
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v4.0.0-alpha.8
    hooks:
      - id: prettier
        files: ^frontend/
""",
    )
    write(
        ".env.example",
        """# Application
APP_ENV=development
APP_NAME=AI Developer Copilot Platform

# Backend
DATABASE_URL=postgresql+asyncpg://copilot:copilot@localhost:5432/copilot
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256

# Object Storage
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=copilot-artifacts

# LLM (placeholders — inject via secrets manager in production)
LLM_API_KEY=
EMBEDDING_API_KEY=

# GitHub App (placeholders)
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api/v1
""",
    )


def build_backend_config() -> None:
    write(
        "backend/pyproject.toml",
        """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ai-copilot-backend"
version = "0.1.0"
description = "AI-Powered Developer Copilot Platform — Backend"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "redis>=5.2.0",
    "celery>=5.4.0",
    "qdrant-client>=1.12.0",
    "httpx>=0.28.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "structlog>=24.4.0",
    "prometheus-client>=0.21.0",
    "opentelemetry-api>=1.28.0",
    "opentelemetry-sdk>=1.28.0",
    "opentelemetry-instrumentation-fastapi>=0.49b0",
    "python-multipart>=0.0.17",
    "boto3>=1.35.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "types-passlib",
]

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
""",
    )
    write(
        "backend/Dockerfile",
        """FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir hatchling && pip install --no-cache-dir .

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    )
    write(
        "backend/.env.example",
        """DATABASE_URL=postgresql+asyncpg://copilot:copilot@postgres:5432/copilot
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
JWT_SECRET_KEY=change-me-in-production
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
""",
    )
    write(
        "backend/alembic.ini",
        """[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""",
    )
    write(
        "backend/alembic/env.py",
        py_module(
            "Alembic async migration environment.",
            "from logging.config import fileConfig\n\n"
            "from alembic import context\n\n"
            "config = context.config\n"
            "if config.config_file_name is not None:\n"
            "    fileConfig(config.config_file_name)\n\n"
            "target_metadata = None  # Wired in Phase 3: Database Layer\n\n\n"
            "def run_migrations_offline() -> None:\n"
            '    """Run migrations in offline mode."""\n'
            "    url = config.get_main_option('sqlalchemy.url')\n"
            "    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)\n"
            "    with context.begin_transaction():\n"
            "        context.run_migrations()\n\n\n"
            "def run_migrations_online() -> None:\n"
            '    """Run migrations in online mode."""\n'
            "    raise NotImplementedError('Async migration runner wired in Phase 3')\n\n\n"
            "if context.is_offline_mode():\n"
            "    run_migrations_offline()\n"
            "else:\n"
            "    run_migrations_online()\n",
        ),
    )
    write(
        "backend/alembic/script.py.mako",
        '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
''',
    )
    write("backend/alembic/versions/.gitkeep", "")


def build_frontend() -> None:
    vue_shell = '<template>\n  <div />\n</template>\n\n<script setup lang="ts">\n</script>\n'
    write("frontend/index.html", """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Developer Copilot Platform</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
""")
    write(
        "frontend/package.json",
        """{
  "name": "ai-copilot-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts",
    "type-check": "vue-tsc --noEmit"
  },
  "dependencies": {
    "axios": "^1.7.9",
    "pinia": "^2.3.0",
    "vue": "^3.5.13",
    "vue-router": "^4.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.17",
    "typescript": "~5.7.2",
    "vite": "^6.0.5",
    "vue-tsc": "^2.2.0"
  }
}
""",
    )
    write(
        "frontend/tsconfig.json",
        """{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue"]
}
""",
    )
    write(
        "frontend/vite.config.ts",
        """import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
""",
    )
    write(
        "frontend/tailwind.config.ts",
        """import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: { extend: {} },
  plugins: [],
} satisfies Config
""",
    )
    write(
        "frontend/postcss.config.js",
        """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
""",
    )
    write(
        "frontend/Dockerfile",
        """FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
""",
    )
    write(
        "frontend/.env.example",
        """VITE_API_BASE_URL=http://localhost:8000/api/v1
""",
    )
    write(
        "frontend/src/main.ts",
        """import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
""",
    )
    write(
        "frontend/src/App.vue",
        """<template>
  <AppLayout>
    <router-view />
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from '@/shared/components/AppLayout.vue'
</script>
""",
    )
    write(
        "frontend/src/assets/main.css",
        """@tailwind base;
@tailwind components;
@tailwind utilities;
""",
    )
    write(
        "frontend/src/router/index.ts",
        """import { createRouter, createWebHistory } from 'vue-router'
import { authGuard } from './guards/auth.guard'
import { rbacGuard } from './guards/rbac.guard'
import { authRoutes } from './routes/auth.routes'
import { repositoryRoutes } from './routes/repository.routes'
import { chatRoutes } from './routes/chat.routes'
import { analysisRoutes } from './routes/analysis.routes'
import { dashboardRoutes } from './routes/dashboard.routes'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    ...authRoutes,
    ...repositoryRoutes,
    ...chatRoutes,
    ...analysisRoutes,
    ...dashboardRoutes,
  ],
})

router.beforeEach(authGuard)
router.beforeEach(rbacGuard)

export default router
""",
    )
    write("frontend/src/router/guards/auth.guard.ts", "// Auth navigation guard — implemented in Phase 4b\n")
    write("frontend/src/router/guards/rbac.guard.ts", "// RBAC navigation guard — implemented in Phase 4b\n")

    route_files = {
        "auth.routes.ts": "auth",
        "repository.routes.ts": "repository",
        "chat.routes.ts": "chat",
        "analysis.routes.ts": "analysis",
        "dashboard.routes.ts": "dashboard",
    }
    for fname, mod in route_files.items():
        write(
            f"frontend/src/router/routes/{fname}",
            f"import type {{ RouteRecordRaw }} from 'vue-router'\n\n"
            f"export const {mod}Routes: RouteRecordRaw[] = []\n",
        )

    stores = ["auth", "tenant", "repository", "analysis", "chat", "dashboard", "ui"]
    for s in stores:
        write(
            f"frontend/src/stores/{s}.store.ts",
            f"import {{ defineStore }} from 'pinia'\n\n"
            f"export const use{s.capitalize()}Store = defineStore('{s}', {{\n"
            f"  state: () => ({{}}),\n"
            f"}})\n",
        )

    apis = [
        "client",
        "auth",
        "repository",
        "analysis",
        "agent",
        "finding",
        "chat",
        "rag",
        "github",
        "dashboard",
    ]
    for a in apis:
        if a == "client":
            write(
                "frontend/src/api/client.ts",
                """import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

export default apiClient
""",
            )
        else:
            write(f"frontend/src/api/{a}.api.ts", f"// {a} API client — implemented in Phase 4b\n")

    types = [
        "auth",
        "repository",
        "analysis",
        "agent",
        "finding",
        "chat",
        "dashboard",
        "common",
    ]
    for t in types:
        write(f"frontend/src/types/{t}.types.ts", f"// {t} TypeScript types\n")

    composables = [
        "useSSE",
        "usePermission",
        "usePagination",
        "useJobPoller",
        "useRepositoryScope",
    ]
    for c in composables:
        write(f"frontend/src/composables/{c}.ts", f"// {c} composable\n")

    module_views = {
        "auth": ["LoginView", "RegisterView", "GitHubCallbackView"],
        "repository": ["RepositoryListView", "RepositoryDetailView", "RepositoryUploadView"],
        "chat": ["ChatView"],
        "analysis": ["AnalysisView", "FindingDetailView"],
        "dashboard": ["RepositoryDashboardView", "AnalyticsDashboardView"],
        "settings": ["ProfileSettingsView", "TeamSettingsView", "GitHubSettingsView"],
    }
    module_components = {
        "auth": ["LoginForm", "RegisterForm"],
        "repository": ["RepositoryCard", "IndexStatusBadge", "UploadDropzone", "GitHubConnectButton"],
        "chat": [
            "ChatSidebar",
            "ChatThread",
            "ChatInput",
            "ChatMessage",
            "ChatCitation",
            "ScopeSelector",
            "AgentInlineResult",
        ],
        "analysis": [
            "AnalysisTriggerPanel",
            "AgentStatusGrid",
            "FindingList",
            "FindingCard",
            "FindingFilter",
            "SeverityBadge",
        ],
        "dashboard": [
            "HealthScoreCard",
            "TrendChart",
            "AgentUsageChart",
            "TokenUsageChart",
            "MetricSummaryPanel",
        ],
        "settings": ["RoleManagementTable", "GitHubInstallationCard", "APIKeyManager"],
    }
    for mod, views in module_views.items():
        for v in views:
            write(f"frontend/src/modules/{mod}/views/{v}.vue", vue_shell)
    for mod, comps in module_components.items():
        for c in comps:
            write(f"frontend/src/modules/{mod}/components/{c}.vue", vue_shell)

    shared_components = [
        "AppLayout",
        "AppSidebar",
        "AppHeader",
        "BaseButton",
        "BaseInput",
        "BaseModal",
        "BaseTable",
        "BasePagination",
        "BaseToast",
        "LoadingSpinner",
        "EmptyState",
        "ErrorBoundary",
        "CodeBlock",
    ]
    for c in shared_components:
        write(f"frontend/src/shared/components/{c}.vue", vue_shell)
    write("frontend/src/shared/icons/.gitkeep", "")


def build_docker() -> None:
    write(
        "docker/docker-compose.yml",
        """services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: copilot
      POSTGRES_PASSWORD: copilot
      POSTGRES_DB: copilot
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U copilot"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.12.5
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    env_file:
      - ../backend/.env.example
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_started

  celery-indexing:
    build:
      context: ../backend
    command: celery -A app.infrastructure.tasks.celery_app worker -Q indexing_queue -l info
    env_file:
      - ../backend/.env.example
    depends_on:
      - redis
      - postgres

  celery-analysis:
    build:
      context: ../backend
      dockerfile: Dockerfile
    command: celery -A app.infrastructure.tasks.celery_app worker -Q analysis_queue -l info
    env_file:
      - ../backend/.env.example
    depends_on:
      - redis
      - postgres

  celery-agent:
    build:
      context: ../backend
      dockerfile: Dockerfile
    command: celery -A app.infrastructure.tasks.celery_app worker -Q agent_queue -l info
    env_file:
      - ../backend/.env.example
    depends_on:
      - redis
      - postgres
      - qdrant

  celery-beat:
    build:
      context: ../backend
      dockerfile: Dockerfile
    command: celery -A app.infrastructure.tasks.celery_app beat -l info
    env_file:
      - ../backend/.env.example
    depends_on:
      - redis

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    ports:
      - "5173:80"
    depends_on:
      - backend

  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  qdrant_data:
  minio_data:
""",
    )
    write(
        "docker/docker-compose.test.yml",
        """services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: copilot_test
    tmpfs:
      - /var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  qdrant:
    image: qdrant/qdrant:v1.12.5
""",
    )
    write(
        "docker/docker-compose.prod.yml",
        """services:
  backend:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 2G

  celery-indexing:
    deploy:
      replicas: 2

  celery-analysis:
    deploy:
      replicas: 2

  celery-agent:
    deploy:
      replicas: 3
""",
    )
    write(
        "docker/nginx/nginx.conf",
        """worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 100m;

    include /etc/nginx/conf.d/*.conf;
}
""",
    )
    write(
        "docker/nginx/conf.d/default.conf",
        """upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:80;
}

server {
    listen 80;
    server_name localhost;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /webhooks/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
    }
}
""",
    )


def build_github_workflows() -> None:
    write(
        ".github/workflows/ci.yml",
        """name: CI

on:
  pull_request:
    branches: [main, develop]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        working-directory: backend
        run: pip install -e ".[dev]"
      - name: Ruff lint
        working-directory: backend
        run: ruff check .
      - name: MyPy
        working-directory: backend
        run: mypy app
      - name: Unit tests
        working-directory: backend
        run: pytest tests/unit -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Install and type-check
        working-directory: frontend
        run: |
          npm ci
          npm run type-check
""",
    )
    write(
        ".github/workflows/build.yml",
        """name: Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build backend image
        run: docker build -t ai-copilot-backend:latest ./backend
      - name: Build frontend image
        run: docker build -t ai-copilot-frontend:latest ./frontend
""",
    )
    write(
        ".github/workflows/deploy-staging.yml",
        """name: Deploy Staging

on:
  workflow_run:
    workflows: [Build]
    types: [completed]
    branches: [main]

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Helm upgrade staging
        run: echo "helm upgrade ai-copilot infrastructure/helm/ai-copilot -f infrastructure/helm/ai-copilot/values.staging.yaml"
""",
    )
    write(
        ".github/workflows/deploy-production.yml",
        """name: Deploy Production

on:
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Helm upgrade production
        run: echo "helm upgrade ai-copilot infrastructure/helm/ai-copilot -f infrastructure/helm/ai-copilot/values.production.yaml"
""",
    )
    write(
        ".github/workflows/dependency-scan.yml",
        """name: Dependency Scan

on:
  schedule:
    - cron: '0 6 * * 1'
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: pip-audit
        run: pip install pip-audit && pip-audit -r backend/pyproject.toml || true
      - name: npm audit
        working-directory: frontend
        run: npm audit --audit-level=high || true
""",
    )
    write(
        ".github/workflows/migration-check.yml",
        """name: Migration Check

on:
  pull_request:
    paths:
      - 'backend/alembic/**'

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Alembic migrations
        working-directory: backend
        run: echo "alembic check"
""",
    )


def build_infrastructure() -> None:
    k8s_files = {
        "k8s/namespaces/staging.yaml": """apiVersion: v1
kind: Namespace
metadata:
  name: ai-copilot-staging
""",
        "k8s/namespaces/production.yaml": """apiVersion: v1
kind: Namespace
metadata:
  name: ai-copilot-production
""",
        "k8s/deployments/backend.yaml": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  labels:
    app: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: ai-copilot-backend:latest
          ports:
            - containerPort: 8000
""",
        "k8s/deployments/celery-indexing-worker.yaml": "# Celery indexing worker deployment skeleton\n",
        "k8s/deployments/celery-analysis-worker.yaml": "# Celery analysis worker deployment skeleton\n",
        "k8s/deployments/celery-agent-worker.yaml": "# Celery agent worker deployment skeleton\n",
        "k8s/deployments/celery-beat.yaml": "# Celery beat deployment skeleton\n",
        "k8s/deployments/nginx.yaml": "# NGINX deployment skeleton\n",
        "k8s/services/backend-service.yaml": """apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
""",
        "k8s/services/nginx-service.yaml": "# NGINX service skeleton\n",
        "k8s/configmaps/app-config.yaml": "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: app-config\ndata: {}\n",
        "k8s/hpa/backend-hpa.yaml": "# Backend HPA skeleton\n",
        "k8s/hpa/celery-indexing-hpa.yaml": "# Celery indexing HPA skeleton\n",
        "k8s/hpa/celery-analysis-hpa.yaml": "# Celery analysis HPA skeleton\n",
        "k8s/hpa/celery-agent-hpa.yaml": "# Celery agent HPA skeleton\n",
        "k8s/ingress/staging-ingress.yaml": "# Staging ingress skeleton\n",
        "k8s/ingress/production-ingress.yaml": "# Production ingress skeleton\n",
    }
    for path, content in k8s_files.items():
        write(f"infrastructure/{path}", content)

    write(
        "infrastructure/helm/ai-copilot/Chart.yaml",
        """apiVersion: v2
name: ai-copilot
description: AI-Powered Developer Copilot Platform Helm chart
type: application
version: 0.1.0
appVersion: "0.1.0"
""",
    )
    write(
        "infrastructure/helm/ai-copilot/values.yaml",
        """replicaCount:
  backend: 2
  celeryIndexing: 2
  celeryAnalysis: 2
  celeryAgents: 3

image:
  backend:
    repository: ai-copilot-backend
    tag: latest
  frontend:
    repository: ai-copilot-frontend
    tag: latest

ingress:
  enabled: true
  host: copilot.local

resources: {}
""",
    )
    write("infrastructure/helm/ai-copilot/values.staging.yaml", "# Staging overrides\nreplicaCount:\n  backend: 1\n")
    write("infrastructure/helm/ai-copilot/values.production.yaml", "# Production overrides\nreplicaCount:\n  backend: 3\n")

    helm_templates = [
        "deployment-backend.yaml",
        "deployment-celery-indexing.yaml",
        "deployment-celery-analysis.yaml",
        "deployment-celery-agents.yaml",
        "deployment-celery-beat.yaml",
        "service.yaml",
        "hpa.yaml",
        "ingress.yaml",
        "configmap.yaml",
        "serviceaccount.yaml",
    ]
    for t in helm_templates:
        write(f"infrastructure/helm/ai-copilot/templates/{t}", f"# Helm template: {t}\n")

    write("infrastructure/terraform/main.tf", '# Terraform root module\nterraform {\n  required_version = ">= 1.6.0"\n}\n')
    write("infrastructure/terraform/variables.tf", "# Terraform variables\n")
    write("infrastructure/terraform/outputs.tf", "# Terraform outputs\n")
    write("infrastructure/terraform/backend.tf", '# Terraform state backend\n# terraform {\n#   backend "s3" {}\n# }\n')

    tf_modules = ["networking", "database", "redis", "qdrant", "storage", "container_registry", "secrets"]
    for m in tf_modules:
        write(f"infrastructure/terraform/modules/{m}/main.tf", f'# Module: {m}\n')
        write(f"infrastructure/terraform/modules/{m}/variables.tf", "")
        write(f"infrastructure/terraform/modules/{m}/outputs.tf", "")

    write("infrastructure/terraform/envs/staging/main.tf", '# Staging environment\n')
    write("infrastructure/terraform/envs/production/main.tf", '# Production environment\n')

    write("infrastructure/monitoring/prometheus/prometheus.yaml", "# Prometheus configuration skeleton\n")
    write("infrastructure/monitoring/prometheus/rules/backend-alerts.yaml", "# Backend alert rules\n")
    write("infrastructure/monitoring/prometheus/rules/celery-alerts.yaml", "# Celery alert rules\n")
    write("infrastructure/monitoring/prometheus/rules/agent-alerts.yaml", "# Agent alert rules\n")
    write("infrastructure/monitoring/grafana/datasources/.gitkeep", "")
    write(
        "infrastructure/monitoring/grafana/dashboards/backend-overview.json",
        '{"title": "Backend Overview", "panels": []}\n',
    )
    write(
        "infrastructure/monitoring/grafana/dashboards/celery-workers.json",
        '{"title": "Celery Workers", "panels": []}\n',
    )
    write(
        "infrastructure/monitoring/grafana/dashboards/agent-performance.json",
        '{"title": "Agent Performance", "panels": []}\n',
    )
    write(
        "infrastructure/monitoring/grafana/dashboards/rag-retrieval.json",
        '{"title": "RAG Retrieval", "panels": []}\n',
    )
    write("infrastructure/monitoring/loki/loki-config.yaml", "# Loki configuration skeleton\n")


def main() -> None:
    ensure_dirs()
    copy_docs()
    build_root_files()
    build_python_stubs()
    build_backend_config()
    build_frontend()
    build_docker()
    build_github_workflows()
    build_infrastructure()
    print(f"Scaffold generated at {ROOT}")


if __name__ == "__main__":
    main()
