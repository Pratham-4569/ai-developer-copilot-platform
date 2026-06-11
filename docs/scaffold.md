# scaffold.md — AI-Powered Developer Copilot Platform

> **Document Type:** Repository Structure & Architectural Boundaries
> **Status:** Canonical — Must be followed before any implementation begins
> **Source Documents:** Constitution v1.0 · PRD v1.0 · Architecture v1.0 · Database v1.0 · API v1.0 · Roadmap v1.0 · LLM Contract v1.0
> **Output Path:** `docs/scaffold.md`

---

## Table of Contents

1. [Monorepo Structure](#1-monorepo-structure)
2. [Backend Structure](#2-backend-structure)
3. [LangGraph Agent Structure](#3-langgraph-agent-structure)
4. [Frontend Structure](#4-frontend-structure)
5. [Infrastructure Structure](#5-infrastructure-structure)
6. [Module Ownership](#6-module-ownership)
7. [Layer Dependency Rules](#7-layer-dependency-rules)
8. [Naming Conventions](#8-naming-conventions)
9. [Future Feature Placement Rules](#9-future-feature-placement-rules)
10. [Repository Blueprint Summary](#10-repository-blueprint-summary)

---

## 1. Monorepo Structure

The repository is a monorepo. All code, infrastructure, documentation, and tooling for the platform lives in a single repository root. There is no package-based sub-repo splitting. Each top-level directory has exclusive ownership of its concern.

```
ai-copilot-platform/                         # Repository root
│
├── backend/                                 # FastAPI application — all Python source
├── frontend/                                # Vue 3 SPA — all TypeScript/Vue source
├── infrastructure/                          # IaC, Kubernetes, Helm, Terraform
├── docker/                                  # Docker Compose files and NGINX config
├── .github/                                 # GitHub Actions CI/CD workflows
├── docs/                                    # All project documentation
│   ├── scaffold.md                          # THIS FILE — canonical structure reference
│   ├── architecture.md                      # System architecture (source of truth)
│   ├── prd.md                               # Product requirements (source of truth)
│   ├── database.md                          # Database schema (source of truth)
│   ├── api.md                               # API specification (source of truth)
│   ├── roadmap.md                           # Implementation roadmap (source of truth)
│   ├── constitution.md                      # Project vision & constraints
│   └── llm_contract.md                      # AI assistant implementation contract
│
├── .pre-commit-config.yaml                  # Pre-commit hooks: Ruff, MyPy, Prettier
├── .gitignore
└── README.md
```

**Monorepo rules:**
- `backend/` and `frontend/` are never merged or nested inside each other.
- `docs/` contains only documentation, never source code or configuration.
- `infrastructure/` contains only IaC and deployment manifests, never application code.
- `docker/` contains only compose files and reverse-proxy config, never application code.
- New top-level directories require architectural justification documented in `docs/architecture.md`.

---

## 2. Backend Structure

The backend is a FastAPI application organized into four concentric Clean Architecture layers. Dependency direction is strictly inward: Interface → Application → Domain. Infrastructure implements domain-defined interfaces and may depend on both Domain and Application. No inner layer may import from an outer layer.

```
backend/
│
├── pyproject.toml                           # All Python dependencies, pinned versions
├── Dockerfile                               # Backend container image
├── alembic.ini                              # Alembic migration configuration
│
├── alembic/                                 # Database migration management
│   ├── env.py                               # Alembic async environment setup
│   ├── script.py.mako                       # Migration template
│   └── versions/                            # One file per migration, never edited post-merge
│
├── tests/                                   # Test suite — mirrors app/ structure
│   ├── conftest.py                          # Shared fixtures, async test DB, DI overrides
│   ├── unit/                                # Pure unit tests — no DB, no HTTP, no external calls
│   │   ├── domain/
│   │   ├── application/
│   │   └── agents/
│   ├── integration/                         # Tests with real DB + real Redis (test containers)
│   │   ├── repositories/
│   │   ├── services/
│   │   └── agents/
│   └── e2e/                                 # Full HTTP round-trip tests via TestClient
│       ├── auth/
│       ├── repositories/
│       ├── chat/
│       └── analysis/
│
└── app/                                     # Application source root
    │
    ├── main.py                              # FastAPI app factory — registers middleware, routers, lifespan
    ├── config.py                            # Pydantic BaseSettings — all config from env vars, no defaults for secrets
    ├── dependencies.py                      # FastAPI Depends() providers — DI wiring entry point
    │
    ├── domain/                              # ══ DOMAIN LAYER ══ (innermost — zero framework imports)
    │   │
    │   ├── entities/                        # Pure Python domain entities
    │   │   ├── __init__.py
    │   │   ├── tenant.py                    # Tenant aggregate root
    │   │   ├── user.py                      # User entity + role associations
    │   │   ├── repository.py                # Repository aggregate root + index state machine
    │   │   ├── analysis_job.py              # AnalysisJob aggregate — owns agent run collection
    │   │   ├── agent_finding.py             # AgentFinding value object — canonical finding schema
    │   │   ├── agent_run.py                 # AgentRun entity — per-agent execution record
    │   │   ├── chat_session.py              # ChatSession aggregate + message history
    │   │   ├── chat_message.py              # ChatMessage entity + citation refs
    │   │   └── rag_chunk.py                 # RAGChunk value object — chunk + embedding metadata
    │   │
    │   ├── value_objects/                   # Immutable typed values — no identity, no mutation
    │   │   ├── __init__.py
    │   │   ├── tenant_id.py                 # TenantId — strongly typed UUID wrapper
    │   │   ├── repository_id.py             # RepositoryId — strongly typed UUID wrapper
    │   │   ├── severity.py                  # Severity enum: CRITICAL / HIGH / MEDIUM / LOW / INFO
    │   │   ├── analysis_scope.py            # AnalysisScope — repository / branch / diff / file set
    │   │   ├── agent_type.py                # AgentType enum — all eight agents
    │   │   ├── index_status.py              # IndexStatus enum: pending / indexing / ready / failed
    │   │   ├── job_status.py                # JobStatus enum: pending / running / completed / failed
    │   │   └── confidence_score.py          # ConfidenceScore — validated float 0.0–1.0
    │   │
    │   ├── events/                          # Domain events — published by application, consumed by handlers
    │   │   ├── __init__.py
    │   │   ├── base_event.py                # BaseDomainEvent — id, occurred_at, tenant_id
    │   │   ├── repository_events.py         # RepositoryUploaded · RepositoryIndexed · RepositoryIndexFailed
    │   │   ├── analysis_events.py           # AnalysisJobStarted · AnalysisJobCompleted · AgentCompleted · AgentFailed
    │   │   └── github_events.py             # GitHubPushReceived · GitHubPROpened · GitHubPRUpdated
    │   │
    │   └── interfaces/                      # Abstract repository interfaces — implemented in infrastructure/
    │       ├── __init__.py
    │       ├── tenant_repository.py         # ITenantRepository
    │       ├── user_repository.py           # IUserRepository
    │       ├── repository_repository.py     # IRepositoryRepository
    │       ├── analysis_repository.py       # IAnalysisRepository
    │       ├── agent_run_repository.py      # IAgentRunRepository
    │       ├── finding_repository.py        # IFindingRepository
    │       ├── chat_repository.py           # IChatRepository
    │       ├── rag_chunk_repository.py      # IRAGChunkRepository (Qdrant interface)
    │       ├── audit_repository.py          # IAuditRepository
    │       └── event_outbox_repository.py   # IEventOutboxRepository
    │
    ├── application/                         # ══ APPLICATION LAYER ══ (use cases — no framework, no DB drivers)
    │   │
    │   ├── __init__.py
    │   │
    │   ├── auth/                            # Authentication & RBAC use cases
    │   │   ├── __init__.py
    │   │   ├── auth_service.py              # Register · Login · Logout · Refresh · GitHub OAuth
    │   │   ├── rbac_service.py              # Permission resolution · role assignment · scope enforcement
    │   │   └── token_service.py             # JWT encode/decode · refresh token lifecycle
    │   │
    │   ├── tenant/                          # Tenant lifecycle use cases
    │   │   ├── __init__.py
    │   │   ├── tenant_service.py            # Create · Update · Suspend · Settings management
    │   │   └── tenant_context.py            # TenantContext — propagated on every service call
    │   │
    │   ├── repository/                      # Repository management use cases
    │   │   ├── __init__.py
    │   │   ├── repository_service.py        # Create · List · Get · Update · Delete · Access control
    │   │   └── ingestion_service.py         # ZIP ingestion · GitHub clone · validation · pipeline trigger
    │   │
    │   ├── indexing/                        # Repository indexing orchestration
    │   │   ├── __init__.py
    │   │   ├── indexing_service.py          # Full index · incremental index · status tracking
    │   │   ├── chunking_service.py          # Language-aware chunking strategy selection
    │   │   └── file_filter_service.py       # Binary exclusion · vendor exclusion · path normalization
    │   │
    │   ├── rag/                             # RAG retrieval use cases
    │   │   ├── __init__.py
    │   │   ├── rag_service.py               # Hybrid retrieve · HyDE expansion · RBAC filter · rerank
    │   │   ├── embedding_service.py         # Batch embedding · cache-aware · provider abstraction
    │   │   └── citation_service.py          # Citation token mapping · source metadata assembly
    │   │
    │   ├── chat/                            # Chat use cases
    │   │   ├── __init__.py
    │   │   ├── chat_service.py              # handle_message · intent classification · streaming orchestration
    │   │   ├── session_service.py           # Create · load · update · scope change · history windowing
    │   │   └── scope_resolver.py            # Resolve active scope from session + user request
    │   │
    │   ├── analysis/                        # Analysis orchestration use cases
    │   │   ├── __init__.py
    │   │   ├── analysis_orchestration_service.py  # Trigger · dispatch agents · aggregate · score
    │   │   └── finding_service.py           # Finding CRUD · status update · export · feedback
    │   │
    │   ├── agents/                          # Agent orchestration use cases
    │   │   ├── __init__.py
    │   │   └── agent_orchestration_service.py     # Dispatch · monitor · collect · partial failure handling
    │   │
    │   ├── github/                          # GitHub integration use cases
    │   │   ├── __init__.py
    │   │   ├── github_integration_service.py      # App install · repo connect · sync · webhook dispatch
    │   │   └── pr_review_service.py               # PR diff analysis · comment formatting · GitHub API post
    │   │
    │   ├── dashboard/                       # Dashboard & analytics use cases
    │   │   ├── __init__.py
    │   │   └── dashboard_service.py         # Health scores · agent metrics · token usage · snapshot queries
    │   │
    │   └── audit/                           # Audit logging use cases
    │       ├── __init__.py
    │       └── audit_service.py             # Structured audit write — called from all mutating services
    │
    ├── infrastructure/                      # ══ INFRASTRUCTURE LAYER ══ (framework-aware — implements domain interfaces)
    │   │
    │   ├── __init__.py
    │   │
    │   ├── db/                              # PostgreSQL / SQLAlchemy
    │   │   ├── __init__.py
    │   │   ├── session.py                   # Async sessionmaker · connection pool factory
    │   │   ├── base.py                      # SQLAlchemy declarative base
    │   │   ├── models/                      # ORM models — one file per domain table group
    │   │   │   ├── __init__.py
    │   │   │   ├── auth_models.py           # users · roles · permissions · role_permissions · user_roles · refresh_tokens
    │   │   │   ├── tenant_models.py         # tenants · tenant_settings · user_repository_access
    │   │   │   ├── repository_models.py     # repositories · repository_index_runs
    │   │   │   ├── analysis_models.py       # analysis_jobs · agent_runs · agent_findings · finding_feedback · finding_rag_sources
    │   │   │   ├── rag_models.py            # rag_chunk_metadata
    │   │   │   ├── chat_models.py           # chat_sessions · chat_messages · chat_message_citations · chat_message_feedback
    │   │   │   ├── github_models.py         # github_installations · github_repository_links · github_webhook_events · github_pr_reviews · github_issues_pushed
    │   │   │   ├── dashboard_models.py      # repository_health_snapshots · agent_utilization_daily
    │   │   │   └── audit_models.py          # audit_log_entries · domain_events_outbox
    │   │   │
    │   │   └── repositories/               # Concrete repository implementations (implement domain interfaces)
    │   │       ├── __init__.py
    │   │       ├── tenant_repository.py
    │   │       ├── user_repository.py
    │   │       ├── repository_repository.py
    │   │       ├── analysis_repository.py
    │   │       ├── agent_run_repository.py
    │   │       ├── finding_repository.py
    │   │       ├── chat_repository.py
    │   │       ├── audit_repository.py
    │   │       └── event_outbox_repository.py
    │   │
    │   ├── vector/                          # Qdrant vector store
    │   │   ├── __init__.py
    │   │   ├── qdrant_client.py             # Qdrant async client factory · collection management
    │   │   └── qdrant_chunk_repository.py   # IRAGChunkRepository implementation — upsert · hybrid search · filter
    │   │
    │   ├── cache/                           # Redis cache layer
    │   │   ├── __init__.py
    │   │   ├── redis_client.py              # Redis async client factory
    │   │   └── cache_adapter.py             # get · set · delete · TTL management · key namespacing
    │   │
    │   ├── storage/                         # Object storage (S3-compatible)
    │   │   ├── __init__.py
    │   │   └── object_storage_adapter.py    # Upload · download · delete · presigned URL · tenant prefix enforcement
    │   │
    │   ├── llm/                             # LLM & embedding provider adapters
    │   │   ├── __init__.py
    │   │   ├── llm_adapter.py               # Streaming · non-streaming · retry · token counting · provider abstraction
    │   │   └── embedding_adapter.py         # Batch embed · cache-aware · dense + sparse · provider abstraction
    │   │
    │   ├── github/                          # GitHub API adapter
    │   │   ├── __init__.py
    │   │   ├── github_api_adapter.py        # REST calls · App auth · webhook signature verification
    │   │   └── github_app_auth.py           # JWT generation · installation token management
    │   │
    │   ├── events/                          # Domain event publishing infrastructure
    │   │   ├── __init__.py
    │   │   └── event_publisher.py           # Transactional outbox publish · Celery task dispatch
    │   │
    │   └── tasks/                           # Celery task definitions (thin wrappers — delegate to application services)
    │       ├── __init__.py
    │       ├── celery_app.py                # Celery app factory · broker URL · result backend · queue routing
    │       ├── celery_beat_schedule.py      # Periodic task schedule — stale index checks, snapshot jobs
    │       ├── indexing_tasks.py            # index_repository · incremental_reindex · delete_index
    │       ├── analysis_tasks.py            # run_analysis_job · aggregate_findings · compute_health_scores
    │       ├── agent_tasks.py               # run_agent (dispatched per AgentType) · agent_chord_callback
    │       ├── github_tasks.py              # process_webhook · post_pr_review · push_github_issues
    │       └── maintenance_tasks.py         # partition_management · audit_archival · snapshot_generation
    │
    ├── interfaces/                          # ══ INTERFACE LAYER ══ (outermost — HTTP boundary)
    │   │
    │   ├── __init__.py
    │   │
    │   ├── api/                             # FastAPI route handlers
    │   │   ├── __init__.py
    │   │   └── v1/                          # Version 1 — all routes under /api/v1/
    │   │       ├── __init__.py
    │   │       ├── router.py                # Aggregates all v1 sub-routers
    │   │       ├── auth.py                  # /auth/* endpoints
    │   │       ├── tenants.py               # /tenants/* endpoints (admin only)
    │   │       ├── repositories.py          # /repositories/* endpoints
    │   │       ├── analysis.py              # /analysis/* endpoints + job status + SSE stream
    │   │       ├── agents.py                # /agents/* endpoints — invoke + run status + findings
    │   │       ├── chat.py                  # /chat/* endpoints — sessions + SSE message stream
    │   │       ├── rag.py                   # /rag/* endpoints — retrieve + index status
    │   │       ├── github.py                # /github/* endpoints — connect + sync + settings
    │   │       └── dashboard.py             # /dashboard/* endpoints — health scores + analytics
    │   │
    │   ├── webhooks/                        # External webhook receivers (separate from versioned API)
    │   │   ├── __init__.py
    │   │   └── github_webhook.py            # POST /webhooks/github — signature verify + event dispatch
    │   │
    │   ├── schemas/                         # Pydantic request/response schemas (API contract)
    │   │   ├── __init__.py
    │   │   ├── auth_schemas.py
    │   │   ├── tenant_schemas.py
    │   │   ├── repository_schemas.py
    │   │   ├── analysis_schemas.py
    │   │   ├── agent_schemas.py
    │   │   ├── finding_schemas.py
    │   │   ├── chat_schemas.py
    │   │   ├── rag_schemas.py
    │   │   ├── github_schemas.py
    │   │   ├── dashboard_schemas.py
    │   │   └── common_schemas.py            # Pagination · error responses · job references · health
    │   │
    │   └── middleware/                      # FastAPI middleware stack (registered in main.py)
    │       ├── __init__.py
    │       ├── auth_middleware.py           # JWT decode · user context injection
    │       ├── tenant_middleware.py         # Tenant ID extraction · tenant context injection
    │       ├── rbac_middleware.py           # Permission enforcement per route
    │       ├── audit_middleware.py          # Structured audit log write on every mutating request
    │       ├── rate_limit_middleware.py     # Per-tenant rate limiting via Redis
    │       └── request_logging_middleware.py # Structured request/response logging with trace IDs
    │
    └── agents/                              # ══ LANGGRAPH AGENT IMPLEMENTATIONS ══ (see Section 3)
        └── (see Section 3 for full hierarchy)
```

---

## 3. LangGraph Agent Structure

All eight agents live under `backend/app/agents/`. Each agent is a self-contained LangGraph state machine. They share a base class, state schema, and common node implementations but are independently deployable as Celery tasks.

```
backend/app/agents/
│
├── __init__.py
│
├── base/                                    # Shared agent foundation — all agents inherit from here
│   ├── __init__.py
│   ├── base_agent.py                        # Abstract base: build_graph() · run() · get_node_registry()
│   ├── agent_state.py                       # Shared TypedDict AgentState — input/output/intermediate fields
│   ├── agent_config.py                      # AgentConfig dataclass — scope · thresholds · model params
│   ├── agent_nodes.py                       # Shared node implementations: retriever_node · reflector_node · schema_validator_node
│   ├── agent_output.py                      # AgentOutput Pydantic model — findings list + metadata + confidence
│   └── agent_exceptions.py                  # AgentRetrievalError · AgentSchemaError · AgentMaxRetryError
│
├── shared/                                  # Cross-agent utilities (not nodes — utilities called inside nodes)
│   ├── __init__.py
│   ├── prompt_library.py                    # All agent system prompts as typed constants — never inlined in agents
│   ├── retrieval_profiles.py                # Per-agent retrieval config: chunk types · filters · top-k values
│   ├── finding_schema.py                    # Canonical AgentFinding Pydantic schema (shared across all agents)
│   ├── severity_classifier.py               # Shared severity scoring logic
│   └── output_formatter.py                  # Shared finding serialization and deduplication logic
│
├── orchestration/                           # Agent orchestration layer
│   ├── __init__.py
│   ├── orchestrator.py                      # Celery group dispatch · chord callback · partial failure isolation
│   ├── scope_resolver.py                    # Translate AnalysisScope into per-agent retrieval boundaries
│   └── result_aggregator.py                 # Deduplicate cross-agent findings · compute composite health scores
│
├── architecture/                            # Architecture Agent
│   ├── __init__.py
│   ├── architecture_agent.py                # LangGraph graph definition: plan → retrieve → reason → reflect → output
│   ├── architecture_planner.py              # Decomposes architecture review into sub-queries
│   ├── architecture_reasoner.py             # LLM reasoning node with architecture-specific system prompt
│   └── architecture_output.py              # Architecture-specific finding schema extensions
│
├── code_review/                             # Code Review Agent
│   ├── __init__.py
│   ├── code_review_agent.py
│   ├── code_review_planner.py
│   ├── code_review_reasoner.py
│   └── code_review_output.py
│
├── bug_detection/                           # Bug Detection Agent
│   ├── __init__.py
│   ├── bug_detection_agent.py
│   ├── bug_detection_planner.py
│   ├── bug_detection_reasoner.py
│   └── bug_detection_output.py
│
├── security/                                # Security Agent
│   ├── __init__.py
│   ├── security_agent.py
│   ├── security_planner.py                  # Targets: dep manifests · auth code · input handling · secrets
│   ├── security_reasoner.py
│   └── security_output.py                   # OWASP / CVE category tagging
│
├── documentation/                           # Documentation Agent
│   ├── __init__.py
│   ├── documentation_agent.py
│   ├── documentation_planner.py
│   ├── documentation_reasoner.py
│   └── documentation_output.py             # Generates docstrings · README sections · API descriptions
│
├── test_generation/                         # Test Generation Agent
│   ├── __init__.py
│   ├── test_generation_agent.py
│   ├── test_generation_planner.py
│   ├── test_generation_reasoner.py
│   └── test_generation_output.py           # Produces test stubs + coverage gap findings
│
├── issue_generation/                        # Issue Generation Agent
│   ├── __init__.py
│   ├── issue_generation_agent.py
│   ├── issue_generation_planner.py
│   ├── issue_generation_reasoner.py
│   └── issue_generation_output.py          # Structured GitHub Issue payloads
│
└── refactoring/                             # Refactoring Agent
    ├── __init__.py
    ├── refactoring_agent.py
    ├── refactoring_planner.py
    ├── refactoring_reasoner.py
    └── refactoring_output.py                # Refactoring suggestions with before/after diff context
```

### Agent State Model

Every agent operates on a shared `AgentState` TypedDict defined in `base/agent_state.py`. The state flows through all LangGraph nodes without mutation — nodes return partial state updates that LangGraph merges.

**Mandatory state fields (all agents):**
- `tenant_id`, `repository_id`, `analysis_job_id`, `agent_run_id`
- `scope` (AnalysisScope value object)
- `plan` (list of retrieval sub-queries)
- `retrieved_chunks` (list of RAGChunk with metadata)
- `reasoning_output` (raw LLM response)
- `reflection_passed` (bool)
- `retry_count` (int — max 2 retrieval retries)
- `findings` (list of AgentFinding — final structured output)
- `schema_valid` (bool)
- `error` (Optional[str])

### Agent Execution Contract

Every agent **must**:
1. Extend `BaseAgent` from `base/base_agent.py`.
2. Implement `build_graph() -> CompiledGraph`.
3. Accept `AgentConfig` at construction — never read config from environment directly.
4. Produce findings conforming to `finding_schema.AgentFinding` before persistence.
5. Run as a Celery task via `agent_tasks.run_agent` — never called synchronously from HTTP handlers.
6. Isolate failures — an exception inside one agent must not affect sibling agents.

---

## 4. Frontend Structure

The Vue 3 SPA uses the Composition API throughout. All state is managed via Pinia stores. API communication is mediated by typed API client modules — components never call `fetch` or `axios` directly.

```
frontend/
│
├── package.json                             # Dependencies: Vue 3 · Vite · TypeScript · Pinia · Vue Router · Tailwind
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── Dockerfile                               # Frontend container (multi-stage: build → NGINX static serve)
│
└── src/
    │
    ├── main.ts                              # App entry point — mounts Vue, registers plugins
    ├── App.vue                              # Root component — router-view + global layout
    │
    ├── router/                              # Vue Router
    │   ├── index.ts                         # Route definitions + navigation guards (auth + RBAC)
    │   ├── guards/
    │   │   ├── auth.guard.ts                # Redirect unauthenticated users
    │   │   └── rbac.guard.ts                # Redirect users without required permission
    │   └── routes/                          # Route configs grouped by module
    │       ├── auth.routes.ts
    │       ├── repository.routes.ts
    │       ├── chat.routes.ts
    │       ├── analysis.routes.ts
    │       └── dashboard.routes.ts
    │
    ├── stores/                              # Pinia stores — one store per domain module
    │   ├── auth.store.ts                    # JWT · user profile · permissions · refresh
    │   ├── tenant.store.ts                  # Tenant context · settings
    │   ├── repository.store.ts              # Repository list · active repository · index status
    │   ├── analysis.store.ts                # Analysis jobs · agent run status · findings
    │   ├── chat.store.ts                    # Sessions · messages · active scope · streaming state
    │   ├── dashboard.store.ts               # Health scores · agent metrics · snapshots
    │   └── ui.store.ts                      # Global UI state: loading · toasts · modals · sidebar
    │
    ├── api/                                 # Typed API client modules — one per backend resource
    │   ├── client.ts                        # Base Axios/Fetch instance — auth header injection · error interceptor
    │   ├── auth.api.ts
    │   ├── repository.api.ts
    │   ├── analysis.api.ts
    │   ├── agent.api.ts
    │   ├── finding.api.ts
    │   ├── chat.api.ts
    │   ├── rag.api.ts
    │   ├── github.api.ts
    │   └── dashboard.api.ts
    │
    ├── types/                               # TypeScript type definitions mirroring backend schemas
    │   ├── auth.types.ts
    │   ├── repository.types.ts
    │   ├── analysis.types.ts
    │   ├── agent.types.ts
    │   ├── finding.types.ts
    │   ├── chat.types.ts
    │   ├── dashboard.types.ts
    │   └── common.types.ts                  # Pagination · JobStatus · Severity · AgentType enums
    │
    ├── composables/                         # Reusable Composition API logic — no UI, no store access
    │   ├── useSSE.ts                        # Server-Sent Events subscription with cleanup
    │   ├── usePermission.ts                 # RBAC permission check from auth store
    │   ├── usePagination.ts                 # Cursor/page pagination state management
    │   ├── useJobPoller.ts                  # Poll job status until terminal state
    │   └── useRepositoryScope.ts            # Active repository + scope context
    │
    ├── modules/                             # Feature modules — each owns its views + module-specific components
    │   │
    │   ├── auth/                            # Authentication module
    │   │   ├── views/
    │   │   │   ├── LoginView.vue
    │   │   │   ├── RegisterView.vue
    │   │   │   └── GitHubCallbackView.vue
    │   │   └── components/
    │   │       ├── LoginForm.vue
    │   │       └── RegisterForm.vue
    │   │
    │   ├── repository/                      # Repository management module
    │   │   ├── views/
    │   │   │   ├── RepositoryListView.vue
    │   │   │   ├── RepositoryDetailView.vue
    │   │   │   └── RepositoryUploadView.vue
    │   │   └── components/
    │   │       ├── RepositoryCard.vue
    │   │       ├── IndexStatusBadge.vue
    │   │       ├── UploadDropzone.vue
    │   │       └── GitHubConnectButton.vue
    │   │
    │   ├── chat/                            # Repository-Aware Chat module
    │   │   ├── views/
    │   │   │   └── ChatView.vue
    │   │   └── components/
    │   │       ├── ChatSidebar.vue          # Session list + new session
    │   │       ├── ChatThread.vue           # Message history + streaming indicator
    │   │       ├── ChatInput.vue            # Message composer + scope selector
    │   │       ├── ChatMessage.vue          # Single message with citation rendering
    │   │       ├── ChatCitation.vue         # Source citation chip — file + line range
    │   │       ├── ScopeSelector.vue        # Repository / branch / file scope picker
    │   │       └── AgentInlineResult.vue    # Renders structured agent output inside chat
    │   │
    │   ├── analysis/                        # Analysis & agent findings module
    │   │   ├── views/
    │   │   │   ├── AnalysisView.vue         # Trigger + status + results for a repository
    │   │   │   └── FindingDetailView.vue
    │   │   └── components/
    │   │       ├── AnalysisTriggerPanel.vue
    │   │       ├── AgentStatusGrid.vue      # 8-agent status grid with live updates
    │   │       ├── FindingList.vue
    │   │       ├── FindingCard.vue
    │   │       ├── FindingFilter.vue        # Filter by agent · severity · status · file
    │   │       └── SeverityBadge.vue
    │   │
    │   ├── dashboard/                       # Dashboards & analytics module
    │   │   ├── views/
    │   │   │   ├── RepositoryDashboardView.vue    # Technical debt · security · complexity · test coverage
    │   │   │   └── AnalyticsDashboardView.vue     # Agent usage · token consumption · cost tracking
    │   │   └── components/
    │   │       ├── HealthScoreCard.vue
    │   │       ├── TrendChart.vue
    │   │       ├── AgentUsageChart.vue
    │   │       ├── TokenUsageChart.vue
    │   │       └── MetricSummaryPanel.vue
    │   │
    │   └── settings/                        # Settings module
    │       ├── views/
    │       │   ├── ProfileSettingsView.vue
    │       │   ├── TeamSettingsView.vue
    │       │   └── GitHubSettingsView.vue
    │       └── components/
    │           ├── RoleManagementTable.vue
    │           ├── GitHubInstallationCard.vue
    │           └── APIKeyManager.vue
    │
    └── shared/                              # Shared UI components — no module-specific logic
        ├── components/
        │   ├── AppLayout.vue                # Shell: sidebar + header + main slot
        │   ├── AppSidebar.vue
        │   ├── AppHeader.vue
        │   ├── BaseButton.vue
        │   ├── BaseInput.vue
        │   ├── BaseModal.vue
        │   ├── BaseTable.vue
        │   ├── BasePagination.vue
        │   ├── BaseToast.vue
        │   ├── LoadingSpinner.vue
        │   ├── EmptyState.vue
        │   ├── ErrorBoundary.vue
        │   └── CodeBlock.vue                # Syntax-highlighted code renderer for findings + citations
        └── icons/                           # SVG icon components
```

---

## 5. Infrastructure Structure

```
infrastructure/
│
├── k8s/                                     # Kubernetes raw manifests (non-Helm environments)
│   ├── namespaces/
│   │   ├── staging.yaml
│   │   └── production.yaml
│   ├── deployments/
│   │   ├── backend.yaml
│   │   ├── celery-indexing-worker.yaml
│   │   ├── celery-analysis-worker.yaml
│   │   ├── celery-agent-worker.yaml
│   │   ├── celery-beat.yaml
│   │   └── nginx.yaml
│   ├── services/
│   │   ├── backend-service.yaml
│   │   └── nginx-service.yaml
│   ├── configmaps/
│   │   └── app-config.yaml
│   ├── hpa/                                 # Horizontal Pod Autoscaler definitions
│   │   ├── backend-hpa.yaml
│   │   ├── celery-indexing-hpa.yaml
│   │   ├── celery-analysis-hpa.yaml
│   │   └── celery-agent-hpa.yaml
│   └── ingress/
│       ├── staging-ingress.yaml
│       └── production-ingress.yaml
│
├── helm/                                    # Helm chart for environment-portable deploys
│   └── ai-copilot/
│       ├── Chart.yaml
│       ├── values.yaml                      # Default values — no secrets
│       ├── values.staging.yaml
│       ├── values.production.yaml
│       └── templates/
│           ├── deployment-backend.yaml
│           ├── deployment-celery-indexing.yaml
│           ├── deployment-celery-analysis.yaml
│           ├── deployment-celery-agents.yaml
│           ├── deployment-celery-beat.yaml
│           ├── service.yaml
│           ├── hpa.yaml
│           ├── ingress.yaml
│           ├── configmap.yaml
│           └── serviceaccount.yaml
│
├── terraform/                               # Cloud infrastructure provisioning
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── modules/
│   │   ├── networking/                      # VPC · subnets · security groups
│   │   ├── database/                        # Managed PostgreSQL + read replica
│   │   ├── redis/                           # Managed Redis cluster
│   │   ├── qdrant/                          # Qdrant deployment (managed or self-hosted)
│   │   ├── storage/                         # Object storage bucket + lifecycle
│   │   ├── container_registry/              # ECR / ACR / GCR
│   │   └── secrets/                         # Secrets manager setup
│   ├── envs/
│   │   ├── staging/
│   │   └── production/
│   └── backend.tf                           # Terraform state backend config
│
└── monitoring/                              # Observability stack configuration
    ├── prometheus/
    │   ├── prometheus.yaml
    │   └── rules/
    │       ├── backend-alerts.yaml
    │       ├── celery-alerts.yaml
    │       └── agent-alerts.yaml
    ├── grafana/
    │   ├── datasources/
    │   └── dashboards/
    │       ├── backend-overview.json
    │       ├── celery-workers.json
    │       ├── agent-performance.json
    │       └── rag-retrieval.json
    └── loki/
        └── loki-config.yaml

docker/
│
├── docker-compose.yml                       # Full local development stack
├── docker-compose.test.yml                  # Isolated test environment (no persistent volumes)
├── docker-compose.prod.yml                  # Production service overrides
└── nginx/
    ├── nginx.conf                           # Upstream config · SSL termination · rate limiting
    └── conf.d/
        └── default.conf

.github/
│
└── workflows/
    ├── ci.yml                               # Trigger: pull_request → lint · type-check · unit tests · integration tests · security scan
    ├── build.yml                            # Trigger: push to main → Docker build + push to registry
    ├── deploy-staging.yml                   # Trigger: build success → Helm upgrade staging + smoke tests
    ├── deploy-production.yml                # Trigger: manual approval → Helm upgrade production + health probe
    ├── dependency-scan.yml                  # Scheduled: weekly → pip-audit + npm audit
    └── migration-check.yml                  # Trigger: pull_request → validate Alembic migration backward compat
```

---

## 6. Module Ownership

### Domain Layer (`app/domain/`)

**Responsibility:** Defines what the system *is* — core business concepts, their invariants, and the interfaces through which they are accessed.

**Belongs here:**
- Entity classes representing core business objects (Repository, AnalysisJob, Tenant, User, ChatSession)
- Value objects (Severity, AnalysisScope, TenantId)
- Domain events (RepositoryIndexed, AnalysisJobCompleted)
- Abstract repository interfaces (ITenantRepository, IFindingRepository)
- Domain-level validation rules expressed as entity methods

**Must never belong here:**
- Any import from FastAPI, SQLAlchemy, Celery, Redis, Qdrant, or any infrastructure library
- HTTP request/response schemas (Pydantic schemas live in `interfaces/schemas/`)
- Business logic that spans multiple aggregates (that belongs in application services)
- Database queries of any kind

---

### Application Layer (`app/application/`)

**Responsibility:** Orchestrates domain objects to fulfil use cases. Coordinates reads and writes via domain repository interfaces. Publishes domain events.

**Belongs here:**
- Application service classes (one per bounded context module)
- Use case methods (e.g., `ingest_repository`, `handle_chat_message`, `dispatch_analysis`)
- Cross-entity business logic (e.g., computing a composite health score from multiple agent findings)
- Domain event publication via the event publisher interface
- Tenant context propagation enforcement

**Must never belong here:**
- Direct SQLAlchemy session usage or ORM model references
- Qdrant client calls
- Redis client calls
- HTTP request/response handling
- Celery task definitions
- LLM or embedding API calls (those go through infrastructure adapters)

---

### Infrastructure Layer (`app/infrastructure/`)

**Responsibility:** Implements all interfaces defined by the domain. Knows about frameworks, drivers, and external services. Provides Celery task wrappers.

**Belongs here:**
- SQLAlchemy ORM models
- Concrete repository implementations using SQLAlchemy
- Qdrant repository implementation
- Redis cache adapter
- LLM and embedding provider adapters
- GitHub API adapter
- Object storage adapter
- Celery task definitions (thin wrappers that delegate to application services)
- Domain event publisher implementation

**Must never belong here:**
- Business logic
- HTTP route handling
- Pydantic request/response schemas
- Direct application service composition (DI does that in `dependencies.py`)

---

### Interface Layer (`app/interfaces/`)

**Responsibility:** The HTTP boundary. Receives requests, validates input via Pydantic schemas, calls application services, and returns responses.

**Belongs here:**
- FastAPI route handler functions
- Pydantic request and response schemas
- Middleware implementations (auth, RBAC, tenant, audit, rate limit)
- Webhook receiver endpoints
- SSE streaming response wrappers

**Must never belong here:**
- Business logic of any kind
- Direct database access
- Direct calls to Qdrant, Redis, or LLM clients
- Cross-module service composition (that is done in `dependencies.py`)
- Domain entity construction (handlers receive data, call services, return schemas)

---

### Agents (`app/agents/`)

**Responsibility:** LangGraph state machine implementations for all eight AI agents. Each agent is self-contained and independently executable as a Celery task.

**Belongs here:**
- LangGraph graph definitions
- Agent-specific planner, reasoner, and output formatter classes
- Shared base class, state schema, and shared node implementations
- Agent orchestration (Celery group dispatch, chord callbacks, result aggregation)
- Shared prompt library and retrieval profiles

**Must never belong here:**
- Direct HTTP handling
- Direct database writes (agents write via application service interfaces)
- Shared application service logic (agents call `RAGService` and `FindingService` via injected interfaces)
- UI-specific formatting logic

---

### Frontend Module (`src/modules/<module>/`)

**Responsibility:** Owns all views and module-specific components for one feature area.

**Belongs here:**
- Views (routed pages) for this module
- Components used only within this module

**Must never belong here:**
- Store definitions (those live in `src/stores/`)
- API client logic (those live in `src/api/`)
- TypeScript type definitions shared across modules (those live in `src/types/`)
- Components used by more than one module (those live in `src/shared/components/`)

---

### Shared Frontend (`src/shared/`)

**Responsibility:** Reusable UI components and composables with no module-specific knowledge.

**Belongs here:**
- Generic UI components (BaseButton, BaseModal, AppLayout)
- Reusable composables (useSSE, usePermission, usePagination)

**Must never belong here:**
- Module-specific business logic
- Direct API calls
- Store access (composables may accept store references as arguments, never import them directly)

---

## 7. Layer Dependency Rules

### Backend Dependency Direction

```
Interface Layer
    │  may import: Application Layer, Schemas
    │  must not import: Domain entities directly, Infrastructure, Agents (except via DI)
    ▼
Application Layer
    │  may import: Domain Layer (entities, interfaces, events, value objects)
    │  must not import: Infrastructure, Interface, FastAPI, SQLAlchemy, Redis, Celery
    ▼
Domain Layer
       may import: Python stdlib only
       must not import: anything outside domain/
```

```
Infrastructure Layer
    may import: Domain Layer, Application Layer (interfaces only)
    must not import: Interface Layer
    is imported by: Application Layer via Dependency Injection (never direct)
```

```
Agents Layer
    may import: Application Layer (RAGService, FindingService interfaces), Domain Layer
    must not import: Infrastructure Layer directly, Interface Layer
    is imported by: Infrastructure tasks/ (via Celery task wrappers)
```

### Dependency Injection Boundary

All wiring of concrete infrastructure implementations to application service interfaces happens in `app/dependencies.py`. This is the only file permitted to import from both `application/` and `infrastructure/` simultaneously. No other file may bridge these layers.

### Frontend Dependency Direction

```
Views (modules/<m>/views/)
    may import: module components, shared components, composables, stores, types
    must not import: api/ directly (use stores or composables that wrap api/)

Components (modules/<m>/components/ and shared/components/)
    may import: shared components, composables, types
    must not import: stores directly (receive data as props or use composables)
    must not import: api/ directly

Stores (stores/)
    may import: api/, types
    must not import: components, views

Composables (composables/)
    may import: types, stores (as arguments, not imports)
    must not import: components, views, api/ directly
```

### Forbidden Import Patterns

| Pattern | Reason |
|---|---|
| Route handler imports SQLAlchemy model | Bypasses service layer |
| Application service imports ORM model | Breaks Clean Architecture |
| Domain entity imports FastAPI or Pydantic | Pollutes domain with framework |
| Agent imports Celery directly | Agents must be framework-agnostic; Celery wraps them |
| Two modules import each other's internal services | Circular dependency — use domain events |
| Frontend component calls `fetch` directly | Bypasses typed API client layer |
| Frontend view imports from another module's `components/` | Tight module coupling — move to `shared/` |

---

## 8. Naming Conventions

### Python — Files

| Artifact | Convention | Example |
|---|---|---|
| Domain entity | `<entity_name>.py` | `analysis_job.py` |
| Application service | `<module>_service.py` | `chat_service.py` |
| Infrastructure repository | `<entity>_repository.py` | `finding_repository.py` |
| Infrastructure adapter | `<service>_adapter.py` | `llm_adapter.py` |
| Celery task module | `<domain>_tasks.py` | `agent_tasks.py` |
| Pydantic schema file | `<module>_schemas.py` | `repository_schemas.py` |
| Domain interface | `<entity>_repository.py` (in `domain/interfaces/`) | `user_repository.py` |
| Domain event file | `<domain>_events.py` | `github_events.py` |
| Agent file | `<agent_name>_agent.py` | `security_agent.py` |

### Python — Classes

| Artifact | Convention | Example |
|---|---|---|
| Domain entity | `PascalCase` noun | `AnalysisJob`, `ChatSession` |
| Value object | `PascalCase` noun | `Severity`, `TenantId` |
| Domain event | `PascalCase` past-tense noun phrase | `RepositoryIndexed`, `AgentCompleted` |
| Domain interface | `I` prefix + `PascalCase` + `Repository` suffix | `IFindingRepository` |
| Application service | `PascalCase` + `Service` suffix | `RAGService`, `AnalysisOrchestrationService` |
| Infrastructure repository | `PascalCase` + `Repository` suffix | `SQLAlchemyFindingRepository` |
| Infrastructure adapter | `PascalCase` + `Adapter` suffix | `LLMAdapter`, `GitHubAPIAdapter` |
| Celery task function | `snake_case` verb phrase | `run_agent_task`, `index_repository` |
| Pydantic request schema | `PascalCase` + `Request` suffix | `CreateRepositoryRequest` |
| Pydantic response schema | `PascalCase` + `Response` suffix | `AnalysisJobResponse` |
| Pydantic internal DTO | `PascalCase` + `DTO` suffix | `ChunkEmbeddingDTO` |
| Agent class | `PascalCase` + `Agent` suffix | `SecurityAgent`, `CodeReviewAgent` |
| Agent node function | `snake_case` + `_node` suffix | `retriever_node`, `reflector_node` |

### TypeScript — Frontend

| Artifact | Convention | Example |
|---|---|---|
| Vue component file | `PascalCase.vue` | `FindingCard.vue` |
| Pinia store file | `<module>.store.ts` | `analysis.store.ts` |
| API client file | `<module>.api.ts` | `repository.api.ts` |
| Type definition file | `<module>.types.ts` | `finding.types.ts` |
| Composable file | `use<Name>.ts` | `useSSE.ts`, `usePermission.ts` |
| Router file | `<module>.routes.ts` | `chat.routes.ts` |
| TypeScript interface | `PascalCase` + `I` prefix for interfaces | `IRepository`, `IFinding` |
| TypeScript enum | `PascalCase` | `Severity`, `AgentType` |

### Infrastructure & Configuration

| Artifact | Convention | Example |
|---|---|---|
| Kubernetes manifest | `<resource>-<name>.yaml` | `deployment-backend.yaml` |
| Helm template | `<resource>-<name>.yaml` | `hpa-celery-agents.yaml` |
| GitHub Actions workflow | `<action>.yml` | `deploy-staging.yml` |
| Celery queue name | `snake_case` | `indexing_queue`, `agent_queue` |
| Redis key prefix | `tenant:{id}:<resource>:<id>` | `tenant:abc:session:xyz` |
| Qdrant collection name | `tenant_{id}_repo_{id}` | `tenant_abc_repo_123` |
| Alembic migration | `{timestamp}_{snake_description}.py` | `20250601_0001_add_finding_status.py` |
| Domain event name (outbox) | `PascalCase` string | `"RepositoryIndexed"` |

---

## 9. Future Feature Placement Rules

The following rules govern where new capabilities must be added without violating the architectural boundaries defined above.

### New AI Agent

1. Create a new subdirectory under `backend/app/agents/<agent_name>/`.
2. Define `<agent_name>_agent.py` extending `BaseAgent`.
3. Add agent type to `domain/value_objects/agent_type.py` enum.
4. Register agent in `agents/orchestration/orchestrator.py` dispatch map.
5. Add Celery task routing in `infrastructure/tasks/agent_tasks.py`.
6. Add API endpoint in `interfaces/api/v1/agents.py` for findings retrieval.
7. Add Pydantic schemas in `interfaces/schemas/agent_schemas.py`.
8. Add frontend components in `frontend/src/modules/analysis/components/`.
9. Never: add agent logic directly to route handlers, services, or Celery task bodies.

### New Data Entity

1. Define domain entity in `domain/entities/<entity>.py`.
2. Define abstract repository interface in `domain/interfaces/<entity>_repository.py`.
3. Create SQLAlchemy ORM model in `infrastructure/db/models/<domain>_models.py`.
4. Implement concrete repository in `infrastructure/db/repositories/<entity>_repository.py`.
5. Create Alembic migration — additive only, backward-compatible.
6. Add repository to DI wiring in `app/dependencies.py`.
7. Never: access ORM model from an application service.

### New API Endpoint

1. Add Pydantic request/response schemas to `interfaces/schemas/<module>_schemas.py`.
2. Add route handler in `interfaces/api/v1/<module>.py`.
3. Implement business logic in an existing or new application service (never in the handler).
4. Add RBAC permission constant if a new permission is needed (`domain/value_objects/` or `application/auth/rbac_service.py`).
5. Update `docs/api.md` before merging.
6. Never: put database queries or LLM calls in a route handler.

### New External Integration

1. Create an adapter in `infrastructure/<service_name>/`.
2. Define the interface the adapter implements in `domain/interfaces/` if the service is called from application services.
3. Register the adapter in `app/dependencies.py`.
4. If the integration publishes domain events, add event types to `domain/events/`.
5. Never: call an external service directly from an application service class constructor.

### New Dashboard or Analytics Metric

1. Add database table (or column on existing table) via backward-compatible Alembic migration.
2. Add ORM model in `infrastructure/db/models/dashboard_models.py`.
3. Add repository interface method in `domain/interfaces/`.
4. Implement in `infrastructure/db/repositories/`.
5. Add to `application/dashboard/dashboard_service.py`.
6. Add API endpoint in `interfaces/api/v1/dashboard.py`.
7. Add Vue component in `frontend/src/modules/dashboard/components/`.
8. Never: compute metrics in a route handler or a Vue component.

### New Background Job

1. Define the task function in the appropriate `infrastructure/tasks/<domain>_tasks.py` file.
2. Ensure the task delegates entirely to an application service — zero business logic in the task body.
3. If periodic, register in `infrastructure/tasks/celery_beat_schedule.py`.
4. Assign to the correct Celery queue (indexing / analysis / agent / maintenance).
5. Ensure the task is idempotent (safe to retry).
6. Never: put business logic, database sessions, or LLM calls directly in a Celery task function.

---

## 10. Repository Blueprint Summary

The following condensed blueprint is the canonical input for Cursor or any scaffolding tool to generate the initial project structure. It reflects all rules defined in this document.

```
ai-copilot-platform/
├── .github/workflows/
│   ├── ci.yml
│   ├── build.yml
│   ├── deploy-staging.yml
│   ├── deploy-production.yml
│   ├── dependency-scan.yml
│   └── migration-check.yml
├── .pre-commit-config.yaml
├── README.md
│
├── docs/
│   ├── scaffold.md
│   ├── architecture.md
│   ├── prd.md
│   ├── database.md
│   ├── api.md
│   ├── roadmap.md
│   ├── constitution.md
│   └── llm_contract.md
│
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.test.yml
│   ├── docker-compose.prod.yml
│   └── nginx/nginx.conf
│
├── infrastructure/
│   ├── helm/ai-copilot/Chart.yaml
│   ├── helm/ai-copilot/values.yaml
│   ├── helm/ai-copilot/values.staging.yaml
│   ├── helm/ai-copilot/values.production.yaml
│   ├── helm/ai-copilot/templates/
│   ├── k8s/namespaces/ k8s/deployments/ k8s/services/ k8s/hpa/ k8s/ingress/
│   ├── terraform/main.tf terraform/variables.tf terraform/modules/
│   └── monitoring/prometheus/ monitoring/grafana/ monitoring/loki/
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/env.py alembic/versions/
│   ├── tests/conftest.py tests/unit/ tests/integration/ tests/e2e/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── dependencies.py
│       │
│       ├── domain/
│       │   ├── entities/tenant.py user.py repository.py analysis_job.py agent_finding.py agent_run.py chat_session.py chat_message.py rag_chunk.py
│       │   ├── value_objects/tenant_id.py repository_id.py severity.py analysis_scope.py agent_type.py index_status.py job_status.py confidence_score.py
│       │   ├── events/base_event.py repository_events.py analysis_events.py github_events.py
│       │   └── interfaces/tenant_repository.py user_repository.py repository_repository.py analysis_repository.py agent_run_repository.py finding_repository.py chat_repository.py rag_chunk_repository.py audit_repository.py event_outbox_repository.py
│       │
│       ├── application/
│       │   ├── auth/auth_service.py rbac_service.py token_service.py
│       │   ├── tenant/tenant_service.py tenant_context.py
│       │   ├── repository/repository_service.py ingestion_service.py
│       │   ├── indexing/indexing_service.py chunking_service.py file_filter_service.py
│       │   ├── rag/rag_service.py embedding_service.py citation_service.py
│       │   ├── chat/chat_service.py session_service.py scope_resolver.py
│       │   ├── analysis/analysis_orchestration_service.py finding_service.py
│       │   ├── agents/agent_orchestration_service.py
│       │   ├── github/github_integration_service.py pr_review_service.py
│       │   ├── dashboard/dashboard_service.py
│       │   └── audit/audit_service.py
│       │
│       ├── infrastructure/
│       │   ├── db/session.py base.py
│       │   ├── db/models/auth_models.py tenant_models.py repository_models.py analysis_models.py rag_models.py chat_models.py github_models.py dashboard_models.py audit_models.py
│       │   ├── db/repositories/tenant_repository.py user_repository.py repository_repository.py analysis_repository.py agent_run_repository.py finding_repository.py chat_repository.py audit_repository.py event_outbox_repository.py
│       │   ├── vector/qdrant_client.py qdrant_chunk_repository.py
│       │   ├── cache/redis_client.py cache_adapter.py
│       │   ├── storage/object_storage_adapter.py
│       │   ├── llm/llm_adapter.py embedding_adapter.py
│       │   ├── github/github_api_adapter.py github_app_auth.py
│       │   ├── events/event_publisher.py
│       │   └── tasks/celery_app.py celery_beat_schedule.py indexing_tasks.py analysis_tasks.py agent_tasks.py github_tasks.py maintenance_tasks.py
│       │
│       ├── agents/
│       │   ├── base/base_agent.py agent_state.py agent_config.py agent_nodes.py agent_output.py agent_exceptions.py
│       │   ├── shared/prompt_library.py retrieval_profiles.py finding_schema.py severity_classifier.py output_formatter.py
│       │   ├── orchestration/orchestrator.py scope_resolver.py result_aggregator.py
│       │   ├── architecture/architecture_agent.py architecture_planner.py architecture_reasoner.py architecture_output.py
│       │   ├── code_review/code_review_agent.py code_review_planner.py code_review_reasoner.py code_review_output.py
│       │   ├── bug_detection/bug_detection_agent.py bug_detection_planner.py bug_detection_reasoner.py bug_detection_output.py
│       │   ├── security/security_agent.py security_planner.py security_reasoner.py security_output.py
│       │   ├── documentation/documentation_agent.py documentation_planner.py documentation_reasoner.py documentation_output.py
│       │   ├── test_generation/test_generation_agent.py test_generation_planner.py test_generation_reasoner.py test_generation_output.py
│       │   ├── issue_generation/issue_generation_agent.py issue_generation_planner.py issue_generation_reasoner.py issue_generation_output.py
│       │   └── refactoring/refactoring_agent.py refactoring_planner.py refactoring_reasoner.py refactoring_output.py
│       │
│       └── interfaces/
│           ├── api/v1/router.py auth.py tenants.py repositories.py analysis.py agents.py chat.py rag.py github.py dashboard.py
│           ├── webhooks/github_webhook.py
│           ├── schemas/auth_schemas.py tenant_schemas.py repository_schemas.py analysis_schemas.py agent_schemas.py finding_schemas.py chat_schemas.py rag_schemas.py github_schemas.py dashboard_schemas.py common_schemas.py
│           └── middleware/auth_middleware.py tenant_middleware.py rbac_middleware.py audit_middleware.py rate_limit_middleware.py request_logging_middleware.py
│
└── frontend/
    ├── package.json tsconfig.json vite.config.ts tailwind.config.ts
    ├── Dockerfile
    └── src/
        ├── main.ts App.vue
        ├── router/index.ts guards/auth.guard.ts guards/rbac.guard.ts routes/
        ├── stores/auth.store.ts tenant.store.ts repository.store.ts analysis.store.ts chat.store.ts dashboard.store.ts ui.store.ts
        ├── api/client.ts auth.api.ts repository.api.ts analysis.api.ts agent.api.ts finding.api.ts chat.api.ts rag.api.ts github.api.ts dashboard.api.ts
        ├── types/auth.types.ts repository.types.ts analysis.types.ts agent.types.ts finding.types.ts chat.types.ts dashboard.types.ts common.types.ts
        ├── composables/useSSE.ts usePermission.ts usePagination.ts useJobPoller.ts useRepositoryScope.ts
        ├── modules/
        │   ├── auth/views/ components/
        │   ├── repository/views/ components/
        │   ├── chat/views/ components/
        │   ├── analysis/views/ components/
        │   ├── dashboard/views/ components/
        │   └── settings/views/ components/
        └── shared/
            ├── components/AppLayout.vue AppSidebar.vue AppHeader.vue BaseButton.vue BaseInput.vue BaseModal.vue BaseTable.vue BasePagination.vue BaseToast.vue LoadingSpinner.vue EmptyState.vue ErrorBoundary.vue CodeBlock.vue
            └── icons/
```

---

### Non-Negotiable Scaffold Constraints

The following constraints apply to every implementation decision made within this repository and may not be overridden by any individual or tool:

1. The four Clean Architecture layers (`domain/`, `application/`, `infrastructure/`, `interfaces/`) must never be collapsed, merged, or circumvented.
2. All eight LangGraph agents must remain as independent modules under `app/agents/`. No agent may be merged into another or removed.
3. The RAG system (`application/rag/`, `infrastructure/vector/`) must remain as a shared service consumed by agents, chat, and analysis. It must not be duplicated into individual agent implementations.
4. Multi-tenancy enforcement (`tenant_id` on every query) must be preserved in every infrastructure repository implementation.
5. RBAC (`rbac_middleware.py`, `rbac_service.py`) must remain active on all authenticated API routes.
6. Audit logging (`audit_middleware.py`, `audit_service.py`, `audit_models.py`) must remain on all mutating operations.
7. Celery task bodies must remain as thin wrappers — zero business logic may live in `infrastructure/tasks/`.
8. All secrets (database credentials, API keys, signing keys) must be injected from a secrets manager at runtime. No `.env` file containing real credentials may be committed.
9. Alembic migrations must remain additive and backward-compatible. Destructive schema changes require a documented two-phase migration plan.
10. The `docs/` directory is a first-class project artifact. `scaffold.md`, `architecture.md`, `api.md`, `database.md`, and `roadmap.md` must be updated when structural changes are made, before the implementing PR is merged.

---

*This document is the canonical repository structure reference for the AI-Powered Developer Copilot Platform. All contributors, AI assistants, and scaffolding tools must treat it as the source of truth for where code lives, what belongs where, and what is forbidden where. Deviations require architectural review and documentation before implementation begins.*
