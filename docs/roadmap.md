# Implementation Roadmap

# AI-Powered Developer Copilot Platform

---

| Field             | Detail                                      |
|-------------------|---------------------------------------------|
| Document Version  | 1.0                                         |
| Status            | Draft                                       |
| Product Name      | AI-Powered Developer Copilot Platform       |
| Document Type     | Implementation Roadmap                      |
| Source Documents  | PRD v1.0, Architecture v1.0, Database v1.0, API v1.0 |
| Last Updated      | June 2025                                   |
| Classification    | Internal — Confidential                     |

---

## Table of Contents

1. Project Overview
2. Development Principles
3. Dependency Map
4. Build Order
5. Milestones
6. Deliverables Per Milestone
7. Exit Criteria Per Milestone
8. Risks & Blockers
9. Suggested Git Commit Structure

---

## 1. Project Overview

The AI-Powered Developer Copilot Platform is a production-grade, multi-tenant SaaS system that unifies repository analysis, multi-agent AI orchestration, retrieval-augmented generation (RAG), and developer tooling into a single coherent product. It is purpose-built from an empty repository to a fully deployed Kubernetes-based production service.

The platform is composed of the following major technical systems:

- **FastAPI backend** structured in Clean Architecture layers (Domain → Application → Infrastructure → Interface)
- **Vue 3 SPA frontend** with per-role UI enforcement
- **PostgreSQL** as the primary relational store for all structured state
- **Redis** as the Celery message broker, session cache, and rate-limit store
- **Qdrant** as the vector store for all RAG embeddings, namespaced per tenant and repository
- **Celery workers** (split by job class: indexing, analysis, agents) backed by Celery Beat for scheduling
- **LangGraph agent engine** with eight specialized agents: Architecture, Code Review, Bug Detection, Security, Documentation, Test Generation, Issue Generation, and Refactoring
- **NGINX** as the edge reverse proxy handling SSL termination, routing, and static file serving
- **GitHub App integration** for OAuth, webhook ingestion, PR review posting, and Issues push
- **Kubernetes deployment** with Helm charts, GitHub Actions CI/CD, and blue-green deploy support

The roadmap starts from an empty Git repository and ends with a production-ready, monitored, and hardened SaaS platform. It is sequenced so that every phase has its prerequisites fully satisfied before work begins. Parallel development lanes are explicitly called out where safe.

---

## 2. Development Principles

All implementation work must observe the following principles, derived directly from the architecture document. These are non-negotiable constraints on how the platform is built, not aspirational guidelines.

**Clean Architecture is the law.** Dependency direction flows strictly inward: Interface → Application → Domain. Infrastructure implements domain interfaces. No service class ever imports from a route handler. No route handler contains business logic. Violations of this rule are grounds to reject a pull request.

**Repository Pattern everywhere.** All database access goes through repository classes that implement domain-defined interfaces. Services are not permitted to hold a reference to a SQLAlchemy session or a Qdrant client. They call repository interface methods only.

**Async first.** Every endpoint is `async def`. Every I/O operation — database, vector store, LLM call, object storage, GitHub API — is awaited. Long-running jobs (indexing, analysis, agent execution) are always dispatched to Celery workers and never block the request cycle. The API returns a job reference immediately.

**Tenant ID on every call.** Tenant ID is extracted from the JWT at the API boundary and propagated as a required context parameter through every service method and every repository query. No cross-tenant data access is architecturally possible at the infrastructure layer because every repository query includes a `WHERE tenant_id = :tenant_id` clause.

**Idempotent workers.** Every Celery task (indexing, analysis, agent run) must be safe to retry. If a task fails and is retried, the result must be equivalent to a single successful execution. Use upsert semantics for vector writes and database writes wherever applicable.

**Strict OOP.** Business logic lives in classes. No procedural logic in route handlers, no logic in Pydantic schemas, no raw SQL in service methods. Handlers delegate to services; services orchestrate domain objects and repository interfaces.

**Structured output from all agents.** Every agent produces findings that conform to the `AgentFinding` Pydantic schema: title, description, file paths, line ranges, severity, confidence score, category, and remediation. Schema validation is enforced before any finding is persisted.

**No secrets in source.** All credentials, API keys, signing keys, and database passwords are injected at container runtime from a secrets manager. Nothing sensitive is committed to the repository, even as an example `.env` file.

**Migrations are backward-compatible.** All Alembic schema migrations are additive. `NOT NULL` column additions require a two-step migration: add nullable, backfill, then constrain. Every migration must be deployable without downtime.

---

## 3. Dependency Map

The following map defines which systems must exist before a given system can be started. This is the primary sequencing constraint for the entire roadmap.

```
Project Scaffold
  └── Infrastructure Foundation
        ├── Database Layer (PostgreSQL schema + Alembic)
        │     └── Authentication & RBAC
        │           └── Tenant Management
        │                 └── Repository Management
        │                       ├── Repository Ingestion Pipeline
        │                       │     └── RAG Foundation (Qdrant + Embedding)
        │                       │           └── Repository-Aware Chat
        │                       │                 └── [all agents can be invoked from chat]
        │                       └── Analysis Orchestration Foundation
        │                             └── LangGraph Multi-Agent Foundation
        │                                   ├── Architecture Agent
        │                                   ├── Code Review Agent
        │                                   ├── Bug Detection Agent
        │                                   ├── Security Agent
        │                                   ├── Documentation Agent
        │                                   ├── Test Generation Agent
        │                                   ├── Issue Generation Agent
        │                                   └── Refactoring Agent
        │                                         └── GitHub Integration
        │                                               └── Dashboards & Analytics
        │                                                     └── Observability
        │                                                           └── CI/CD
        │                                                                 └── Production Deployment
        │                                                                       └── Hardening & Optimization
        └── Redis (broker + cache)
        └── Qdrant (vector store cluster)
        └── Object Storage
```

**Parallel development lanes** (can proceed simultaneously once their shared prerequisites are met):

- All eight LangGraph agents can be built in parallel once the Multi-Agent Foundation is complete.
- The Vue frontend can be scaffolded in parallel with backend infrastructure and progressively connected to APIs as they are released.
- The GitHub Integration module can be built in parallel with agents, since it depends only on Repository Management and Analysis Orchestration.
- Observability tooling (logging, metrics, tracing) can be instrumented in parallel with any phase.
- CI/CD pipeline configuration can begin as soon as the project scaffold exists.

**Hard blockers** (must be 100% complete before the next phase begins):

- Database Layer must be complete before Authentication — users, tenants, roles, and refresh tokens all require schema.
- Authentication & RBAC must be complete before every other module — all API endpoints require JWT middleware and tenant context.
- Repository Ingestion Pipeline must be complete before RAG Foundation — there is nothing to embed without ingested content.
- RAG Foundation must be complete before Repository-Aware Chat and all agents — retrieval is the shared backbone.
- LangGraph Multi-Agent Foundation must be complete before any individual agent — the base class, state schema, shared nodes, and orchestration service are prerequisites.
- Analysis Orchestration must be complete before GitHub Integration's PR review feature — PR review is an analysis job triggered by a GitHub webhook.

---

## 4. Build Order

The 23 implementation phases are sequenced below. Each phase is a discrete, testable unit of work. Phases with the same indentation level (where dependencies allow) may be developed in parallel.

| Phase | Name                              | Parallel-Safe With               |
|-------|-----------------------------------|----------------------------------|
| 1     | Project Scaffold                  | —                                |
| 2     | Infrastructure Foundation         | Phase 1 complete                 |
| 3     | Database Layer                    | Frontend Scaffold (Phase 4b)     |
| 4a    | Authentication & RBAC             | —                                |
| 4b    | Vue Frontend Scaffold             | Phase 3 in progress              |
| 5     | Repository Management             | —                                |
| 6     | Repository Ingestion Pipeline     | —                                |
| 7     | RAG Foundation                    | Phase 8 (GitHub scaffold)        |
| 8     | GitHub Integration (scaffold)     | Phase 7                          |
| 9     | Repository-Aware Chat             | Phase 8 GitHub scaffold          |
| 10    | LangGraph Multi-Agent Foundation  | Phase 9 Chat                     |
| 11    | Architecture Agent                | Phases 12–17 (all agents)        |
| 12    | Code Review Agent                 | Phases 11, 13–17                 |
| 13    | Bug Detection Agent               | Phases 11–12, 14–17              |
| 14    | Security Agent                    | Phases 11–13, 15–17              |
| 15    | Documentation Agent               | Phases 11–14, 16–17              |
| 16    | Test Generation Agent             | Phases 11–15, 17                 |
| 17    | Issue Generation Agent            | Phases 11–16                     |
| 18    | Refactoring Agent                 | After Issue Generation complete  |
| 19    | GitHub Integration (full)         | —                                |
| 20    | Dashboards & Analytics            | —                                |
| 21    | Observability                     | Phases 19–20                     |
| 22    | CI/CD                             | Phase 21                         |
| 23    | Production Deployment             | —                                |
| 24    | Hardening & Optimization          | —                                |

---

## 5. Milestones

The 24 phases are grouped into six milestones that mark meaningful, demonstrable progress checkpoints.

| Milestone | Name                               | Phases     | Approximate Duration |
|-----------|------------------------------------|------------|----------------------|
| M1        | Foundation & Auth                  | 1 – 4      | Weeks 1–3            |
| M2        | Repository Ingestion & RAG         | 5 – 7      | Weeks 4–6            |
| M3        | Chat & Agent Infrastructure        | 8 – 10     | Weeks 7–9            |
| M4        | All Eight Agents                   | 11 – 18    | Weeks 10–14          |
| M5        | GitHub, Dashboards & Observability | 19 – 21    | Weeks 15–17          |
| M6        | CI/CD, Production & Hardening      | 22 – 24    | Weeks 18–20          |

---

## 6. Deliverables Per Milestone

---

### Milestone 1 — Foundation & Auth (Phases 1–4)

---

#### Phase 1: Project Scaffold

**Goal:** Establish a clean, opinionated monorepo structure that every engineer will work within for the life of the project. All tooling, linting, formatting, type-checking, and pre-commit hooks are configured here.

**Prerequisites:** Empty repository.

**Components to Build:**
- Repository root with `backend/`, `frontend/`, `docker/`, `.github/`, and `infrastructure/` top-level directories matching the architecture document folder structure exactly.
- `backend/pyproject.toml` with FastAPI, SQLAlchemy (async), Alembic, Celery, LangGraph, Pydantic v2, Ruff, MyPy, pytest, and all other required packages pinned to explicit versions.
- `frontend/package.json` with Vue 3 (Composition API), Vite, TypeScript, Pinia, Vue Router, and testing dependencies.
- `backend/app/main.py` — FastAPI app factory with middleware registration stubs.
- `backend/app/config.py` — Pydantic `BaseSettings` for all environment variables (database URL, Redis URL, Qdrant URL, LLM API key, GitHub App credentials, JWT secrets, object storage config). No defaults for secrets; all required at runtime.
- Pre-commit hooks: Ruff lint + format, MyPy, import sorting.
- `.github/workflows/ci.yml` stub — triggers on pull request; runs lint and type-check.
- `docker/docker-compose.yml` for local development with services: PostgreSQL 15, Redis, Qdrant, and the FastAPI dev server.
- Root `Makefile` with targets: `install`, `dev`, `test`, `lint`, `migrate`.

**Expected Deliverables:**
- Repository with complete folder skeleton.
- `docker compose up` brings up a working local stack with all data services running.
- `make lint` passes on the empty codebase.
- `make test` runs pytest and reports zero tests, zero failures.

---

#### Phase 2: Infrastructure Foundation

**Goal:** Establish the database connection layer, Redis client, Qdrant client, object storage adapter, and async session management. These are the infrastructure primitives that every subsequent phase depends on.

**Prerequisites:** Phase 1 complete.

**Components to Build:**
- `backend/app/infrastructure/db/session.py` — SQLAlchemy async engine and session factory. Two session factories: `async_session_write` (primary) and `async_session_read` (replica). Session is never exposed outside the infrastructure layer.
- `backend/app/infrastructure/cache/redis_client.py` — Async Redis client with tenant-prefixed key helpers (`tenant:{id}:...`).
- `backend/app/infrastructure/vector/qdrant_client.py` — Qdrant async client wrapper. Collection naming convention: `tenant_{id}_repo_{id}`.
- `backend/app/infrastructure/storage/object_storage_adapter.py` — Object storage adapter (S3-compatible). Paths follow `{tenant_id}/{repository_id}/` prefix convention.
- `backend/app/infrastructure/llm/llm_adapter.py` — LLM provider adapter (wraps the configured LLM API). Supports streaming.
- `backend/app/infrastructure/llm/embedding_adapter.py` — Embedding API adapter. Supports batch requests.
- `backend/app/infrastructure/tasks/celery_app.py` — Celery app factory with Redis as broker and result backend. Three named queues: `indexing`, `analysis`, `agents`.
- Health check endpoint `GET /health` — verifies database, Redis, and Qdrant connectivity. Returns `200 OK` with per-service status.
- PgBouncer configuration for local dev compose stack.

**Expected Deliverables:**
- All infrastructure clients initialize and connect on `docker compose up`.
- `GET /health` returns `200 OK` with all services reported as healthy.
- Celery worker starts with `celery -A app.infrastructure.tasks.celery_app worker` with no errors.

---

#### Phase 3: Database Layer

**Goal:** Build the complete PostgreSQL schema for all nine functional domains as defined in the database design document, with all Alembic migrations, indexes, partitioning, and the repository pattern base class.

**Prerequisites:** Phase 2 complete.

**Components to Build:**
- `backend/app/domain/` layer: all domain entities (`Tenant`, `User`, `Repository`, `AnalysisJob`, `AgentFinding`, `ChatSession`, `RAGChunk`), value objects (`Severity`, `AnalysisScope`, `TenantId`), domain repository interfaces (abstract base classes), and domain events.
- SQLAlchemy ORM models in `backend/app/infrastructure/db/models/` for all tables across all nine domains: Auth & RBAC, Tenant Management, Repository Management, Analysis & Agents, RAG Metadata, Chat System, GitHub Integration, Dashboard & Analytics, Audit & Logging.
- Alembic `env.py` configured for async SQLAlchemy and auto-detecting all ORM models.
- Initial migration `001_initial_schema.py` covering all tables with all columns, foreign keys, check constraints, and named indexes as specified in the database document.
- Partitioned tables created with monthly range partitioning: `chat_messages`, `audit_log_entries`, `github_webhook_events`, `repository_health_snapshots`, `agent_findings`.
- Repository pattern base class in `backend/app/infrastructure/db/repositories/` — injects `tenant_id` filter on every read, update, and delete. Supports both write (primary) and read (replica) session routing.
- Concrete repository implementations for all domain repository interfaces.
- `domain_events_outbox` table and relay task stub in Celery Beat.

**Expected Deliverables:**
- `alembic upgrade head` completes without errors against a fresh PostgreSQL 15 instance.
- All tables exist with correct columns, constraints, indexes, and partitioning.
- Repository base class passes unit tests: tenant isolation enforced, cross-tenant query impossible.
- Database migrations are idempotent (run twice with no error).

---

#### Phase 4a: Authentication & RBAC

**Goal:** Implement the complete authentication system (JWT access + refresh tokens, email/password, GitHub OAuth) and RBAC enforcement middleware. This is the security boundary for every subsequent feature.

**Prerequisites:** Phase 3 complete.

**Components to Build:**
- `backend/app/application/auth/auth_service.py` — Registration (user + tenant creation), login, token issuance (RS256/ES256 signed access tokens), refresh token rotation, logout (token revocation), and account lockout after five consecutive failures.
- `backend/app/application/auth/rbac_service.py` — Permission loading from `role_permissions` at startup (cached in Redis). Permission check method used by middleware.
- `backend/app/infrastructure/middleware/auth_middleware.py` — JWT validation on every request (except `/auth/*` and `/webhooks/*`). Injects `user_id`, `tenant_id`, and `permissions` into request state.
- `backend/app/infrastructure/middleware/rbac_middleware.py` — Checks that the authenticated user holds the required permission for the endpoint. Returns `403 Forbidden` with structured error if not.
- `backend/app/infrastructure/middleware/tenant_middleware.py` — Extracts and validates tenant context. Injects into request-scoped context object passed to all services.
- `backend/app/infrastructure/middleware/audit_middleware.py` — Writes to `audit_log_entries` (append-only) for all state-changing requests.
- GitHub OAuth callback handler (`POST /auth/github/callback`).
- API endpoints: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/github/callback`.
- User management APIs: `GET /users/me`, `GET /users`, `POST /users/invite`, `PATCH /users/{id}/role`, `DELETE /users/{id}`.
- Tenant management APIs: `GET /tenants/me`, `PATCH /tenants/me`.
- Rate limiting on auth endpoints (10 req/min register, 20 req/min login per IP).
- Refresh token stored hashed (SHA-256); HTTP-only cookie on the response.

**Expected Deliverables:**
- Full auth flow: register → login → refresh → logout works end-to-end.
- JWT claims include `sub`, `tenant_id`, `role`, `permissions`, `iat`, `exp`.
- RBAC middleware blocks unauthorized access with `403`; allows authorized access.
- Audit log entry written for every login, logout, role change.
- Token expiry and rotation work correctly under automated test.
- Multi-tenancy: user in Tenant A cannot access Tenant B resources.

---

#### Phase 4b: Vue Frontend Scaffold

**Goal:** Establish the Vue 3 SPA structure, routing, Pinia store architecture, auth flow (login/register), and the shared component library. Can begin as soon as Phase 3 is in progress.

**Prerequisites:** Phase 1 complete; Phase 4a API endpoints needed to wire login, but UI scaffold can begin before auth backend is done.

**Components to Build:**
- Vue 3 + Vite + TypeScript + Pinia + Vue Router project in `frontend/src/`.
- Module-based folder structure: `auth/`, `repositories/`, `analysis/`, `chat/`, `agents/`, `dashboard/`, `settings/` — each containing its own views, composables, and Pinia store slices.
- `shared/` directory: composables (useApi, useAuth, usePagination), base components (buttons, modals, tables, status badges, severity chips), and global Pinia stores.
- `router/index.ts` — route definitions with `meta.requiredPermission` on every protected route. Navigation guard checks the authenticated user's permissions against the route requirement and redirects to `403` view if denied.
- `stores/auth.ts` — Pinia store for access token (in-memory), user object, tenant context, and permissions. Token refresh is handled transparently via Axios interceptors.
- `stores/repositories.ts`, `stores/analysis.ts`, `stores/chat.ts`, `stores/dashboard.ts` — module-level stores.
- Login, Register, and Forgot Password views wired to the auth API.
- NGINX `nginx.conf` for the SPA: serves static assets, proxies `/api/` to FastAPI, handles Vue Router's history mode with fallback to `index.html`.
- `frontend/Dockerfile` — multi-stage build: `node:20` build stage, `nginx:alpine` serve stage.

**Expected Deliverables:**
- `docker compose up` serves the Vue SPA at `http://localhost`.
- Login and register flows work end-to-end against the FastAPI auth backend.
- Route guards correctly block pages based on role permissions.
- All module folders exist with placeholder views ready for Phase-by-phase connection.

---

### Milestone 2 — Repository Ingestion & RAG (Phases 5–7)

---

#### Phase 5: Repository Management

**Goal:** Build the repository CRUD layer — the data management foundation that all ingestion, analysis, and chat features act upon.

**Prerequisites:** Phases 3 and 4a complete.

**Components to Build:**
- `backend/app/application/repository/repository_service.py` — Create, read, update, and soft-delete repositories. Enforce per-tenant repository limits (`tenant_settings.max_repositories`). Publish `RepositoryUploaded` domain event on creation.
- ZIP upload endpoint: `POST /repositories/upload` (multipart/form-data, up to 2 GB). Validates MIME type (`application/zip`), stores raw artifact to object storage under `{tenant_id}/{repository_id}/`, creates `repository_index_runs` record with `status=pending`.
- GitHub connect endpoint: `POST /repositories/connect/github` — stores repository link metadata, creates index run record.
- `GET /repositories` — paginated list with status, last sync time, primary language, analysis health summary.
- `GET /repositories/{id}`, `PUT /repositories/{id}`, `DELETE /repositories/{id}` (soft-delete sets `deleted_at`).
- `GET /repositories/{id}/index-runs` — paginated index run history.
- `POST /repositories/{id}/reindex` — triggers a new index run (enqueues Celery task).
- Repository deletion cascade task stub (full implementation in Phase 6): sets `deleted_at`, enqueues `RepositoryDeletionWorker`.
- Repository Management frontend view: list all repositories, status indicators (indexing, ready, error, stale), per-row actions (re-index, delete, view report).
- User repository access table managed via `user_repository_access` — team leads and admins assign developers to repositories.

**Expected Deliverables:**
- ZIP upload accepted and stored in object storage with `index_status = pending`.
- GitHub connect creates the repository record and GitHub link.
- Repository list loads within 2 seconds for up to 100 repositories.
- Soft-delete sets `deleted_at`; repository disappears from all listing queries.
- RBAC enforced: developer cannot upload, only admin/team lead can delete.

---

#### Phase 6: Repository Ingestion Pipeline

**Goal:** Build the complete Celery-based ingestion pipeline that transforms a raw repository artifact (ZIP or GitHub clone) into a normalized, language-tagged, parsed, chunked, embedded, and vector-indexed knowledge base.

**Prerequisites:** Phase 5 complete, Phase 7 (Qdrant + Embedding adapter) initiated enough to accept upserts.

**Components to Build:**
- `backend/app/infrastructure/tasks/indexing_tasks.py` — Celery task `index_repository` that executes the full pipeline and is idempotent.
- Pipeline stages as discrete service methods in `backend/app/application/repository/ingestion_service.py`:
  - **Extraction:** ZIP archive extraction in a sandboxed temp directory (no network access). GitHub clone/pull via the GitHub API adapter.
  - **Normalization:** File path normalization. Exclusion filter for binaries, `node_modules`, `.git`, build artifacts, and vendor directories via configurable rules.
  - **Language Detection:** Per-file language tagging using file extension and content heuristics.
  - **Parsing:** Language-aware AST metadata extraction: function names, class names, imports, docstrings. Metadata attached to chunks.
  - **Chunking:** `backend/app/application/rag/chunking_service.py`. Code files chunked at function/method granularity. Documentation at paragraph level. Config/manifest files as single chunks. Chunk size guardrails (min/max token counts).
  - **Embedding:** `backend/app/application/rag/embedding_service.py`. Batched calls to the embedding API adapter. Both dense (semantic) and sparse (BM25/lexical) representations generated.
  - **Vector Upsert:** `qdrant_vector_repo.py`. Upserts into the tenant-scoped collection (`tenant_{id}_repo_{id}`) with full metadata payload: file path, line range, language, chunk type, repository ID, function/class name.
  - **Status Update:** PostgreSQL `repositories.index_status` transitions: `pending` → `indexing` → `ready` (or `failed`). `index_freshness_at` and `total_chunks` updated. `repository_index_runs` record finalized.
- Domain event publishing: `RepositoryIndexed` on success, `RepositoryIndexFailed` on failure, consumed by domain event outbox relay.
- `RepositoryDeletionWorker` task: deletes all associated rows in dependency order and removes the Qdrant collection on `deleted_at` set.
- Re-indexing logic: incremental mode computes a diff of changed files and upserts only modified chunks. Deleted files are removed from Qdrant.
- Frontend: repository card shows real-time `index_status` via polling `GET /repositories/{id}`.

**Expected Deliverables:**
- ZIP upload triggers indexing pipeline; repository transitions to `ready` within 5 minutes for repos under 100k LOC.
- Qdrant collection for the tenant/repo is populated with correctly chunked, metadata-rich vectors.
- Incremental re-index only processes changed files.
- Deleted repository triggers cascade deletion from all tables and Qdrant within 24 hours.
- Pipeline is retry-safe: failing and restarting a task produces the same correct result.

---

#### Phase 7: RAG Foundation

**Goal:** Build the RAG retrieval system that all agents and the chat module depend on: hybrid dense + sparse retrieval, query rewriting (HyDE), RBAC-enforced scoping, cross-encoder reranking, and citation assembly.

**Prerequisites:** Phase 6 complete (Qdrant populated), embedding adapter from Phase 2.

**Components to Build:**
- `backend/app/application/rag/rag_service.py` — the single entry point for all retrieval. Accepts query text, scope (tenant, repository, optional file/directory filter), and user context. Returns ranked chunks with metadata.
- Query embedding generation — calls the embedding adapter. Checks Redis embedding cache before calling the API.
- Query rewriting / HyDE expansion — for complex or ambiguous queries, generates a hypothetical ideal answer via the LLM adapter and embeds it. Merges the HyDE embedding with the original query embedding.
- Dense vector search — Qdrant ANN search against the tenant-scoped collection. Metadata filter enforces repository and optional file/directory scope.
- Sparse lexical search — Qdrant BM25 search against the same collection.
- Reciprocal Rank Fusion — merges dense and sparse ranked lists into a single ranked list without score normalization.
- RBAC filter — post-retrieval filter confirming retrieved chunk repository IDs are within the user's access grants.
- Cross-encoder reranking — lightweight reranker model applied to the top-N fused results.
- Citation assembly — every returned chunk carries structured metadata: file path, start line, end line, function/class name, repository ID, repository name.
- Query result cache — Redis TTL=60s keyed on hashed query + scope. Cache invalidated on `RepositoryIndexed` event.
- RAG retrieval API: `POST /rag/retrieve` — accepts query and scope, returns ranked chunks. Used for debugging and direct retrieval. Permission: `rag:retrieve`.
- `GET /rag/repositories/{id}/index-status` — returns collection size, freshness timestamp, chunk count.

**Expected Deliverables:**
- `POST /rag/retrieve` returns ranked chunks with file path, line range, and relevance score within 500ms for 95% of queries.
- Hybrid retrieval returns better results on both exact identifier queries and semantic synonym queries than either mode alone (verified manually against test repositories).
- RBAC filter prevents a user with access to Repository A from receiving chunks from Repository B.
- Embedding cache reduces redundant embedding API calls for repeated queries.
- Qdrant collection not found (unindexed repository) returns a structured error, not a 500.

---

### Milestone 3 — Chat & Agent Infrastructure (Phases 8–10)

---

#### Phase 8: Repository-Aware Chat

**Goal:** Build the multi-turn, streaming, SSE-based chat system with session management, scope control, intent classification, and citation rendering.

**Prerequisites:** Phase 7 complete.

**Components to Build:**
- `backend/app/application/chat/session_service.py` — create, load, update, and expire chat sessions. Active session state (history, scope, repository context) stored in Redis with rolling TTL. PostgreSQL used for cold-path hydration if Redis TTL has expired.
- `backend/app/application/chat/chat_service.py` — the main message handling orchestrator. Loads session state, resolves active scope, classifies intent (conversational / factual / agent invocation), calls `RAGService.retrieve()`, assembles LLM prompt (system prompt + windowed history + retrieved context), calls LLM adapter in streaming mode, streams tokens back via SSE, appends turn to session and persists to PostgreSQL.
- History windowing: sliding window of the most recent N turns. Overflow triggers a summarization call to the LLM to compress older turns into a context block.
- Scope propagation: scope changes update Redis session state without resetting history. Next assistant message acknowledges the new scope explicitly.
- Intent classifier: distinguishes agent invocation intent (slash commands or natural language like "review this file for security issues") from standard RAG-grounded questions.
- Slash command parser: `/agent <name> [file:<path>]` syntax for explicit agent invocation.
- SSE streaming endpoint: `POST /chat/sessions/{id}/messages` returns `text/event-stream`. Token events, citation events, and error events are distinct SSE event types.
- Chat APIs: `POST /chat/sessions`, `GET /chat/sessions`, `GET /chat/sessions/{id}`, `DELETE /chat/sessions/{id}`, `PUT /chat/sessions/{id}/scope`, `POST /chat/sessions/{id}/messages/{mid}/feedback`.
- Citation rendering: the LLM is instructed to embed citation tokens; the response post-processor maps tokens to file path + line range metadata and emits structured citation SSE events.
- Chat frontend module: message input with slash command autocomplete, streaming response rendering, citation display (clickable file path → repository file view), scope selector (repository / directory / file / branch), multi-turn history.

**Expected Deliverables:**
- First token of response streamed within 2 seconds under local load.
- Multi-turn conversation correctly maintains context across 20+ turns.
- Every factual response includes at least one source citation with file path and line range.
- Scope changes take effect immediately without resetting conversation history.
- Incorrect response feedback logged to `chat_message_feedback`.

---

#### Phase 9: GitHub Integration (Scaffold)

**Goal:** Build the GitHub App / OAuth connection flow, webhook receiver infrastructure, and repository synchronization trigger. This unblocks the full GitHub integration (PR review, Issues push) that completes in Phase 19.

**Prerequisites:** Phase 5 complete (repository model), Phase 6 complete (indexing pipeline).

**Components to Build:**
- `backend/app/application/github/github_integration_service.py` — GitHub App installation and OAuth connection flows. Stores encrypted installation token and App private key in the secrets manager.
- `backend/app/infrastructure/github/github_api_adapter.py` — wraps the GitHub REST API. Methods: clone repository, list repositories, post PR comment, create issue, verify webhook signature.
- Webhook receiver: `POST /webhooks/github` — HMAC-SHA256 signature validation, deduplication via `github_delivery_id` unique key, stores event payload in `github_webhook_events`, enqueues Celery processing task.
- Webhook event processing task: parses event type (`push`, `pull_request`) and dispatches to the correct handler.
- `push` event handler: triggers incremental re-index on the changed files via the ingestion pipeline.
- `github_installations` and `github_repository_links` tables populated on installation.
- GitHub settings frontend view: connect GitHub App, select repositories, view sync status, disconnect.
- `GET /github/installations`, `POST /github/repositories/{id}/connect`, `DELETE /github/installations/{id}`.

**Expected Deliverables:**
- GitHub App installation flow completes without errors for public and private repositories.
- Push webhook received → incremental re-index begins within 30 seconds.
- Webhook delivery failures retried with exponential backoff.
- Connection revocation in GitHub detected and reflected in platform within 10 minutes.

---

#### Phase 10: LangGraph Multi-Agent Foundation

**Goal:** Build the base agent infrastructure: the abstract agent class, shared state schema, shared node implementations (Planner, Retriever, Reasoner, Reflector, Output Formatter, Schema Validator), the Agent Orchestration Service, and the Celery task dispatch layer. No individual agent is built here — only the foundation all eight agents inherit from.

**Prerequisites:** Phase 7 (RAG), Phase 6 (analysis job persistence).

**Components to Build:**
- `backend/app/agents/base/base_agent.py` — abstract LangGraph agent base class. Defines the standard state machine: Initialize → Plan → Retrieve → Reason → Reflect → FormatOutput → ValidateSchema → Persist → PublishEvent. Subclasses override the Planner (retrieval query decomposition), Reasoner (agent-specific system prompt and output schema), and Output Formatter.
- `backend/app/agents/base/agent_state.py` — shared LangGraph state schema: scope, config, retrieved chunks, reasoning output, findings list, reflection result, retry counts, error state.
- `backend/app/agents/base/agent_nodes.py` — shared node implementations: Retriever (calls `RAGService`), Reflector (LLM self-check call), Schema Validator (Pydantic validation of `AgentFinding` list), Persist (writes findings to `agent_findings` table via finding repository), PublishEvent (emits `AgentCompleted` or `AgentFailed` domain event).
- `AgentFinding` Pydantic schema: title, description, file paths, line ranges, severity (Critical/High/Medium/Low/Informational), confidence (0–100), category, remediation, RAG source references.
- `backend/app/application/agents/agent_orchestration_service.py` — loads agent configuration, resolves analysis scope, dispatches concurrent agent tasks via Celery group. Collects results via Celery chord. Aggregates findings (deduplication, cross-reference). Computes per-agent and composite health scores. Persists `AnalysisJob` result. Emits `AnalysisJobCompleted`.
- `backend/app/application/analysis/analysis_orchestration_service.py` — creates `analysis_jobs` record, determines full vs. incremental scope, invokes the agent orchestration service, handles partial failure (one agent down does not mark the job failed).
- Analysis task: `POST /repositories/{id}/analysis` — accepts scope parameters, triggers analysis job, returns `analysis_job_id` immediately.
- `GET /analysis/{id}` — returns job status, per-agent status, and findings summary.
- `GET /analysis/{id}/stream` — SSE endpoint for live job progress updates.
- Findings APIs: `GET /repositories/{id}/findings`, `GET /findings/{id}`, `PATCH /findings/{id}/status`, `POST /findings/{id}/feedback`, `GET /repositories/{id}/findings/export`.
- Agent invocation API: `POST /agents/invoke` — invokes a named agent on a specific scope. Returns `agent_run_id`.

**Expected Deliverables:**
- Analysis job created and visible in the database with `status=pending`.
- Celery group dispatches N tasks concurrently (one per enabled agent).
- Agent failure is isolated — other agents continue; job is marked `partial` not `failed`.
- `AgentFinding` schema validation rejects malformed output and triggers one retry.
- `GET /analysis/{id}` shows per-agent status in real time.
- Chord callback aggregates findings from all completed agents and computes health scores.

---

### Milestone 4 — All Eight Agents (Phases 11–18)

**All eight agents may be developed in parallel by separate engineers once Phase 10 is complete.** Each agent subclasses `BaseAgent`, overrides the Planner and Reasoner nodes, and is independently testable.

---

#### Phase 11: Architecture Agent

**Goal:** Detect circular dependencies, high coupling, god objects, architectural anti-patterns, and drift. Produce a module dependency map summary and architecture health score.

**Prerequisites:** Phase 10 complete.

**Components to Build:**
- `backend/app/agents/architecture/architecture_agent.py` — Planner decomposes into sub-queries targeting: module entry points, import graphs, inter-module dependency chains, file size and responsibility distribution.
- Reasoner prompt: specialized for architectural pattern recognition, dependency analysis, SOLID principle violation detection, and hexagonal/layered/clean architecture drift.
- Output: architectural findings with affected modules, severity, and specific remediation referencing actual file paths.
- Agent-specific API: `GET /repositories/{id}/agents/architecture/latest`.

---

#### Phase 12: Code Review Agent

**Goal:** Perform logic, maintainability, naming, complexity, and pattern-consistency review on code files or diffs. Post inline GitHub PR comments when triggered via GitHub.

**Prerequisites:** Phase 10 complete. Phase 9 (GitHub scaffold) for PR comment posting.

**Components to Build:**
- `backend/app/agents/code_review/code_review_agent.py` — Planner queries for: file contents (full or diff), existing codebase patterns (naming conventions, design patterns in use, controller/service/repository structure).
- Reasoner prompt: detects logic issues, inconsistencies with established patterns, naming violations, unnecessary complexity, and anti-patterns. Produces per-function/per-file findings.
- PR-scoped mode: operates on diff content, not full repository. Produces inline comments at specific file and line positions.
- PR review verdict: `approve`, `request_changes`, or `informational` based on finding severity.
- Agent-specific APIs: `GET /repositories/{id}/agents/code-review/latest`, `GET /analysis/{id}/agents/code-review/pr-comments`.

---

#### Phase 13: Bug Detection Agent

**Goal:** Identify null pointer risks, unchecked error returns, unhandled promise rejections, race conditions, and runtime failure candidates ranked by likelihood and impact.

**Prerequisites:** Phase 10 complete.

**Components to Build:**
- `backend/app/agents/bug_detection/bug_detection_agent.py` — Planner retrieves: control flow paths, error handling patterns, async/concurrent code sections, cross-function data flow.
- Reasoner prompt: language-aware bug pattern recognition for null dereference (all languages), unchecked error returns (Go), unhandled promise rejections (JS/TS), unchecked exceptions (Java/C#), and race conditions in concurrent code.
- Each finding includes a code snippet showing the problematic pattern and a language-idiomatic suggested fix.
- Agent-specific API: `GET /repositories/{id}/agents/bug-detection/latest`.

---

#### Phase 14: Security Agent

**Goal:** Detect OWASP Top 10 vulnerabilities, exposed secrets and credentials, insecure dependency versions (CVE references), and authorization/authentication flaws. Critical secrets findings trigger immediate UI alerts.

**Prerequisites:** Phase 10 complete.

**Components to Build:**
- `backend/app/agents/security/security_agent.py` — Planner retrieves: authentication/authorization code, input handling paths, dependency manifests (`package.json`, `requirements.txt`, `go.mod`, `pom.xml`, Gemfile), configuration files, cryptography usage.
- Reasoner prompt: OWASP Top 10 pattern detection, secret/credential detection (API keys, tokens, passwords in code and config), insecure cryptography, injection vulnerabilities, and insecure dependency version analysis (CVE cross-reference).
- Secrets findings trigger an immediate high-priority alert event (independent of the analysis cycle) published to the domain event outbox.
- Every Critical and High finding includes a concrete, code-specific remediation code example.
- Agent-specific API: `GET /repositories/{id}/agents/security/latest`.

---

#### Phase 15: Documentation Agent

**Goal:** Identify undocumented functions, classes, and modules; generate accurate docstrings grounded in actual code logic; generate module READMEs and API reference documentation.

**Prerequisites:** Phase 10 complete.

**Components to Build:**
- `backend/app/agents/documentation/documentation_agent.py` — Planner retrieves: all public functions and classes without docstrings, existing README and documentation files, code patterns to infer documentation style.
- Reasoner prompt: generates docstrings that accurately describe the function's purpose, parameters, return values, and raised exceptions — derived from actual code logic. Respects the documentation style (Google, NumPy, JSDoc) detected in the repository.
- Output: generated docstrings as inline code suggestions, module README drafts as markdown artifacts, documentation coverage score.
- Agent-specific API: `GET /repositories/{id}/agents/documentation/latest`.

---

#### Phase 16: Test Generation Agent

**Goal:** Identify untested or undertested code paths and generate compilable unit tests, integration test stubs, and edge case scenarios targeting those gaps.

**Prerequisites:** Phase 10 complete.

**Components to Build:**
- `backend/app/agents/test_generation/test_generation_agent.py` — Planner retrieves: untested functions ranked by complexity/risk, existing test files (to detect framework and conventions), code paths for boundary condition identification.
- Reasoner prompt: generates tests in the detected framework (pytest, Jest, JUnit, etc.), targeting happy paths, null inputs, boundary conditions, and error paths. Does not duplicate existing tests. Includes a brief comment explaining each test's intent.
- Estimated coverage increase calculation included in output.
- Agent-specific API: `GET /repositories/{id}/agents/test-generation/latest`.

---

#### Phase 17: Issue Generation Agent

**Goal:** Translate aggregated agent findings into structured, actionable issue records with assignee suggestions, priority mapping, and deduplication. Enable bulk push to GitHub Issues.

**Prerequisites:** All other agents (Phases 11–16) at least partially complete; Phase 9 GitHub scaffold for Issues push.

**Components to Build:**
- `backend/app/agents/issue_generation/issue_generation_agent.py` — Planner retrieves aggregated findings from all completed agent runs for the current analysis job. No additional RAG retrieval needed — input is the findings database.
- Reasoner: groups related findings, deduplicates across analysis runs (fingerprint matching), assigns priority based on severity mapping (Critical → P0, High → P1, Medium → P2, Low → P3), suggests assignee from git blame data stored in chunk metadata.
- Output: structured issue records with title, description, affected files, severity, priority, category, suggested assignee, and acceptance criteria for resolution.
- GitHub Issues push: `POST /github/issues/push` — pushes selected issues to connected GitHub repository. Handles rate limiting with queued batch execution. Tracks `github_issues_pushed` to prevent duplicates.
- Bulk export: `GET /repositories/{id}/findings/export?format=csv|json`.
- Agent-specific API: `GET /repositories/{id}/agents/issue-generation/latest`.

---

#### Phase 18: Refactoring Agent

**Goal:** Identify high-complexity functions, DRY violations, outdated patterns, and technical debt candidates. Produce ranked refactoring recommendations with before/after code examples.

**Prerequisites:** Phase 10 complete. Must not suggest refactoring for test files unless explicitly scoped.

**Components to Build:**
- `backend/app/agents/refactoring/refactoring_agent.py` — Planner retrieves: code with cyclomatic complexity above configurable threshold, duplicate code blocks above configurable similarity threshold, complex class hierarchies, functions exceeding line-count threshold.
- Reasoner: identifies DRY violations (code duplication), complexity violations, poor naming, and outdated patterns. Produces idiomatic, language-correct refactored code examples for each recommendation.
- Technical debt score: per-module and repository-level. Delta vs. prior analysis run.
- Agent-specific API: `GET /repositories/{id}/agents/refactoring/latest`.

---

### Milestone 5 — GitHub, Dashboards & Observability (Phases 19–21)

---

#### Phase 19: GitHub Integration (Full)

**Goal:** Complete the GitHub integration by activating PR automated review posting, repository synchronization to the PR lifecycle, and GitHub Issues bulk push. This extends the scaffold from Phase 9.

**Prerequisites:** Phase 12 (Code Review Agent), Phase 17 (Issue Generation Agent), Phase 10 (analysis orchestration), Phase 9 (GitHub scaffold).

**Components to Build:**
- `backend/app/application/github/pr_review_service.py` — formats Code Review Agent findings as GitHub review comments at the correct file and line positions. Posts review via GitHub API adapter. Posts summary PR comment with overall verdict and severity breakdown. Sets GitHub PR check status (pass/fail based on configurable severity threshold).
- `pull_request` webhook handler: on `opened` and `synchronize` events, triggers PR-scoped analysis (diff as the analysis target). On `AnalysisJobCompleted`, triggers PR review posting.
- PR check status integration: configurable threshold — if Critical findings exist, check fails and can block merge.
- Re-review triggered automatically on subsequent commits to the PR.
- GitHub Issues push: full implementation connecting `issue_generation_agent` output to GitHub Issues API. Batch push with rate limit handling. Pushed issue URLs stored in `github_issues_pushed`.
- Bot comments clearly labeled as AI-generated.
- Frontend: GitHub integration settings — installation management, PR review threshold configuration, issue push UI.

**Expected Deliverables:**
- PR review comments posted within 3 minutes of PR creation.
- Comments at correct file and line positions.
- PR check status appears in GitHub's required status checks UI.
- Bulk Issues push works for all issues or a user-selected subset.
- Webhook retry with exponential backoff on delivery failure.

---

#### Phase 20: Dashboards & Analytics

**Goal:** Build the Repository Metrics Dashboard and AI Analytics Dashboard, including pre-aggregated snapshot logic, trend charts, export, and the nightly aggregation Celery Beat job.

**Prerequisites:** Phase 10 complete (analysis jobs and findings), Phase 19 (GitHub data).

**Components to Build:**
- `backend/app/application/dashboard/dashboard_service.py` — queries `repository_health_snapshots` (read replica) for metrics. Queries `agent_utilization_daily` for AI analytics. Never queries `agent_findings` or `audit_log_entries` directly for dashboards.
- `repository_health_snapshots` populated by the `AnalysisJobCompleted` event consumer — writes a snapshot row after every analysis run with per-dimension scores (code quality, security, test coverage, documentation coverage, technical debt).
- Celery Beat job: nightly aggregation task populates `agent_utilization_daily` with per-agent run counts, finding counts, acceptance/rejection rates, and average LLM token usage.
- Repository Metrics Dashboard APIs: `GET /dashboard/repositories/{id}/metrics`, `GET /dashboard/repositories/{id}/health-trend`, `GET /dashboard/repositories/{id}/top-findings`.
- AI Analytics Dashboard APIs: `GET /dashboard/analytics/agent-utilization`, `GET /dashboard/analytics/finding-lifecycle`, `GET /dashboard/analytics/chat-usage`, `GET /dashboard/analytics/pr-metrics`.
- Export: all dashboard metrics exportable as CSV. Charts exportable as PNG/SVG (frontend-rendered).
- Repository Metrics Dashboard frontend: overall health score, per-dimension scores, trend charts (7/30/90-day, custom range), top-10 critical findings, test coverage by module, security breakdown by severity.
- AI Analytics Dashboard frontend: agent utilization charts, finding lifecycle metrics, chat usage stats, PR review metrics, user engagement, model feedback rates.
- Dashboard RBAC: Developer role cannot access dashboards; Admin and Team Lead see full detail.

**Expected Deliverables:**
- Dashboard loads within 2 seconds for repositories with up to 1 million LOC.
- All metrics update after each analysis run.
- Trend charts support 7-day, 30-day, 90-day, and custom date ranges.
- All metrics exportable as CSV.
- Nightly aggregation job runs without error and populates `agent_utilization_daily`.

---

#### Phase 21: Observability

**Goal:** Instrument the entire platform with structured logging, distributed tracing, metrics collection, and alerting so that the platform is operable in production.

**Prerequisites:** Phase 19 and Phase 20 underway (need production-like complexity to instrument).

**Components to Build:**
- Structured logging: JSON-format log output from all FastAPI handlers, services, Celery tasks, and agents. Every log line includes: `request_id` (correlation ID propagated from NGINX), `tenant_id`, `user_id`, `trace_id`, log level, component name, and message. No plain text logs.
- Distributed tracing: OpenTelemetry instrumentation on FastAPI (auto-instrumented), SQLAlchemy, Redis, Qdrant client, Celery workers, and LLM adapter calls. Trace IDs propagated across async task boundaries.
- Metrics: Prometheus metrics exposed at `/metrics`. Key counters and histograms: HTTP request duration by endpoint and status code, Celery task duration by task name and queue, LLM API call latency and token count, embedding API call latency, Qdrant query latency, analysis job duration by scope, agent run duration by agent type.
- Alerting rules: P95 chat first-token latency > 3s, analysis job duration > 15 min, agent failure rate > 10% in 1 hour, Celery queue depth > 100 tasks, Qdrant collection not healthy.
- Celery Flower or equivalent: worker monitoring dashboard for queue depths and task status.
- Log aggregation: Loki or equivalent. Dashboards for error rates, slow queries, and failed analysis jobs.
- Tracing backend: Tempo or Jaeger. Trace explorer for debugging slow or failed requests.

**Expected Deliverables:**
- Every request has a `request_id` traceable through all logs.
- Prometheus metrics scraped successfully by monitoring stack.
- Alert rules fire correctly against synthetic threshold violations in staging.
- Distributed traces visible end-to-end from NGINX through FastAPI through Celery task through LLM call.

---

### Milestone 6 — CI/CD, Production & Hardening (Phases 22–24)

---

#### Phase 22: CI/CD

**Goal:** Build the complete GitHub Actions CI/CD pipeline: PR validation, Docker image build and push, staging deployment, manual approval gate, and production deployment with health verification.

**Prerequisites:** Phase 21 complete (observability needed to validate staging deployments).

**Components to Build:**
- `.github/workflows/ci.yml` — triggers on pull request. Stages: Ruff lint, MyPy type-check, `pytest` unit tests, `pytest` integration tests (against dockerized dependencies), dependency security scan (pip-audit / Safety). All stages must pass before merge is permitted.
- `.github/workflows/build.yml` — triggers on push to `main`. Multi-stage Docker builds for `backend` and `frontend` images. Images tagged with `git SHA` and `latest`. Pushed to container registry.
- `.github/workflows/deploy.yml` — `staging` job runs automatically after `build`. `production` job requires manual approval via GitHub Environments. Both jobs use `helm upgrade --install` against the target Kubernetes namespace.
- Helm charts in `infrastructure/k8s/`: `values.yaml` with configurable image tags, replica counts, resource limits, and secret references. Separate `values-staging.yaml` and `values-production.yaml`.
- Smoke test suite: post-deploy health check probe; `GET /health` must return `200 OK`; key E2E flows (register, upload repository, trigger analysis, get findings) must pass.
- Blue-green deployment support: Helm chart supports a traffic-splitting rollout strategy. Old pods stay healthy until health checks pass on new pods.
- Rollback: `helm rollback` triggered automatically if health checks fail within 5 minutes of deployment.
- Secrets injection: Kubernetes secrets (or Vault/AWS Secrets Manager integration) used to mount all credentials at container runtime. No secrets in Helm values files or Git.

**Expected Deliverables:**
- Pull request cannot be merged if CI fails.
- Push to `main` automatically builds and pushes Docker images.
- Staging deployment runs automatically and smoke tests pass.
- Production deployment requires a human to click "Approve" in GitHub.
- Failed production deployment automatically rolls back via Helm.

---

#### Phase 23: Production Deployment

**Goal:** Deploy the complete platform to a production Kubernetes cluster with all data services, worker pools, autoscaling, and network configuration.

**Prerequisites:** Phase 22 complete.

**Components to Build:**
- Kubernetes cluster with separate node pools for API workloads and Celery worker workloads. Worker node pools split by job type: `indexing`, `analysis`, `agents`.
- Production PostgreSQL: managed primary instance with a read replica. PgBouncer deployed in transaction-mode pooling in front of both.
- Production Redis: Redis Cluster for high availability. Separate logical databases for Celery broker, cache, and session state.
- Production Qdrant: cluster with sharding by tenant. TLS enabled for all inter-node communication.
- Object storage: S3-compatible bucket with encryption at rest and versioning enabled.
- Kubernetes HPA configured for FastAPI pods (CPU + request queue depth) and Celery worker pods (queue length per queue).
- NGINX Ingress with TLS termination (cert-manager). Strict request size limits and rate limiting at the edge.
- Secrets management: all secrets injected from AWS Secrets Manager or Vault at container runtime. Rotation policy configured.
- Network policies: inter-service communication restricted to declared service mesh routes. Celery indexing workers have no outbound internet access (sandboxed for ZIP extraction).
- Monitoring stack deployed: Prometheus, Grafana, Loki, Tempo (or equivalent). Pre-built dashboards for all alert rules from Phase 21.
- Runbook documentation: operational procedures for common failure modes.

**Expected Deliverables:**
- Platform deployed and accessible at production domain over HTTPS.
- All health checks green across all services.
- All monitoring dashboards populated with live data.
- Autoscaling verified: load test confirms HPA scales API and worker pods correctly.
- Zero secrets in Kubernetes manifest files or GitHub.

---

#### Phase 24: Hardening & Optimization

**Goal:** Validate all performance, reliability, and security acceptance criteria from the PRD. Address any gaps found during production deployment. Optimize critical paths.

**Prerequisites:** Phase 23 complete.

**Components to Build / Validate:**

**Performance validation and tuning:**
- Load test: confirm chat first-token response < 2 seconds with 1,000 concurrent sessions.
- Load test: confirm dashboard page load < 2 seconds with 50 concurrent users per organization.
- Confirm full analysis of a 500k-LOC repository completes within 10 minutes.
- Confirm incremental analysis on a 500-line diff completes within 3 minutes.
- RAG retrieval P95 latency < 500ms under production load.
- Tune PgBouncer pool sizes, Celery worker concurrency, and Qdrant collection shard counts based on load test results.

**Security hardening:**
- Penetration test or security review: RBAC enforcement, multi-tenant isolation, JWT validation, input sanitization, archive extraction sandbox.
- Verify that no cross-tenant data leakage is possible under any sequence of API calls.
- Confirm that detected secrets in user repositories are never written to platform logs in plain text.
- Dependency scanning: all platform dependencies scanned for known CVEs; critical CVEs remediated.
- Audit log completeness: verify all PRD-required state-changing actions produce audit entries.
- Data deletion: verify that repository deletion removes all associated data from PostgreSQL, Qdrant, and object storage within 24 hours.

**Reliability hardening:**
- Chaos test: kill one Celery worker mid-analysis. Verify partial results are surfaced; job recovers or is marked partial, not failed.
- Chaos test: Redis eviction. Verify chat session hydrates from PostgreSQL correctly.
- Chaos test: Qdrant node failure. Verify query degrades gracefully rather than returning a 500.
- Verify all Celery tasks are retry-safe under simulated task failure.
- Verify 99.9% uptime SLA can be achieved with the current deployment topology.

**Acceptance criteria verification:**
- All acceptance criteria in PRD Section 19 checked off via automated or manual verification and signed off.

**Expected Deliverables:**
- All PRD acceptance criteria verified and documented.
- Performance benchmarks meeting or exceeding SLA targets.
- Security review completed with no unresolved critical or high findings.
- Platform declared production-ready.

---

## 7. Exit Criteria Per Milestone

| Milestone | Exit Criteria |
|-----------|---------------|
| **M1 — Foundation & Auth** | `docker compose up` runs the full local stack. `alembic upgrade head` applies without errors. Register → login → refresh → logout works end-to-end. RBAC middleware blocks unauthorized requests. Audit log entries written for all state-changing auth actions. Vue SPA served at `http://localhost` with working login flow. |
| **M2 — Ingestion & RAG** | ZIP upload ingests a test repository and populates Qdrant with correctly chunked vectors. `POST /rag/retrieve` returns relevant chunks within 500ms. GitHub push webhook triggers incremental re-index within 30 seconds. Repository deletion removes all data within 24 hours. |
| **M3 — Chat & Agent Infrastructure** | Chat session streams first token within 2 seconds. 20-turn conversation maintains correct context. Every response includes source citations. Analysis job created, dispatches concurrent agent tasks, handles single-agent failure gracefully, aggregates results. `GET /analysis/{id}` shows real-time per-agent status. |
| **M4 — All Eight Agents** | All eight agents produce structured `AgentFinding` output conforming to the defined schema. Each agent can be invoked independently via `POST /agents/invoke`. Findings include file path, line range, severity, confidence score, and remediation. GitHub PR review posted within 3 minutes of PR creation. Issues pushed to GitHub Issues. |
| **M5 — GitHub, Dashboards & Observability** | PR review comments posted at correct file and line positions. Dashboard loads within 2 seconds. All metrics update after each analysis run. All metrics exportable. Prometheus metrics scraped. Distributed traces visible end-to-end. All defined alert rules configured. |
| **M6 — CI/CD, Production & Hardening** | Pull request gate enforced in GitHub. Production deployment requires manual approval. Failed deployment triggers automatic rollback. Platform passes all PRD Section 19 acceptance criteria. Performance benchmarks meet SLA targets. Security review complete with no unresolved critical/high findings. |

---

## 8. Risks & Blockers

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **LLM API latency variability** | Chat first-token SLA (< 2s) may be violated under LLM provider load or network degradation | High | Implement response streaming to minimize perceived latency. Cache embedding calls. Set a 4-second timeout with graceful error; surface partial results. Evaluate provider SLAs before production. |
| **Embedding API cost at scale** | Embedding all chunks in large repositories (5M LOC) may be prohibitively expensive | Medium | Batch embedding calls. Cache embeddings keyed on `content_hash`. Only re-embed changed chunks on incremental re-index. Consider a self-hosted embedding model (e.g., `text-embedding-3-small` equivalent) for cost reduction at scale. |
| **Qdrant collection size growth** | Large organizations with many repositories may exhaust Qdrant storage or degrade query latency | Medium | Monitor `repositories.total_chunks` and alert at configurable thresholds. Enforce per-tenant chunk limits in `tenant_settings`. Implement per-tenant collection sharding from the start. |
| **Agent false positive rate** | PRD requires < 20% false positive rate per agent over 30 days. High false positive rates erode user trust | High | Instrument `finding_feedback` from day one. Build false positive rate dashboards in M5. Tune agent system prompts iteratively against false positive metrics. Ship with conservative severity thresholds and allow admin configuration. |
| **LangGraph agent output schema non-compliance** | LLM output may not always conform to the `AgentFinding` schema, causing schema validation failures | Medium | Enforce structured output mode (JSON schema enforcement) on the LLM call. The Schema Validator node retries once before failing the finding. Cap retry cost at one additional LLM call per finding. |
| **GitHub API rate limits** | Bulk PR comment posting and Issues push may hit GitHub's 5,000 req/hour rate limit for GitHub Apps | Medium | Queue bulk GitHub API operations through a rate-limited task in Celery. Track API usage per installation and apply exponential backoff. Split large Issues push into batches of 50. |
| **ZIP archive security (zip bomb / path traversal)** | Malicious ZIP uploads could exhaust disk space or escape the extraction sandbox | High | Extract in a sandboxed container with no network access and a strict disk quota. Validate all extracted paths for path traversal (`../`). Enforce maximum uncompressed size limit before extraction. Run MIME type validation before accepting the upload. |
| **Multi-tenancy data leakage** | A bug in the repository base class could expose one tenant's data to another | Critical | Automated test: for every repository method, assert that tenant_id filter is present in the generated SQL. Integration test: create two tenants, verify neither can access the other's data via any API endpoint. Run this test suite in CI on every PR. |
| **Alembic migration failure in production** | A backward-incompatible migration could cause downtime during deployment | High | All migrations are additive-only. Every migration is tested against a snapshot of production schema in staging before production deploy. Keep a rollback migration for every forward migration. |
| **Celery worker resource contention** | Heavy analysis jobs and LLM-calling agents share worker resources, starving lightweight tasks | Medium | Split Celery workers into three named queues: `indexing`, `analysis`, `agents`. Scale each pool independently. Set per-task rate limits and time limits for agent tasks. |
| **Qdrant collection creation on first index** | If a collection does not exist when the first vector upsert is attempted, the upsert fails | Low | Collection creation is idempotent — attempt `create_collection` with `if_not_exists=True` at the start of every index run. |

---

## 9. Suggested Git Commit Structure

All commits follow the Conventional Commits specification: `<type>(<scope>): <description>`. The `scope` maps directly to the module or phase. Pull requests are squash-merged to `main`. Branch names follow the pattern `phase/<number>-<short-name>` or `feat/<scope>-<description>`.

### Commit Types

| Type | When to Use |
|------|-------------|
| `feat` | New feature or capability added |
| `fix` | Bug fix |
| `chore` | Build, CI, dependency, or configuration change |
| `test` | Test additions or corrections |
| `refactor` | Internal restructuring with no behavior change |
| `docs` | Documentation only |
| `perf` | Performance improvement |
| `security` | Security fix or hardening |
| `migration` | Database migration file |

### Scope Conventions

| Scope | Description |
|-------|-------------|
| `scaffold` | Project scaffold, monorepo structure, tooling |
| `infra` | Infrastructure clients, session factory, health check |
| `db` | ORM models, Alembic migrations, repository base class |
| `auth` | Authentication, JWT, refresh tokens, OAuth |
| `rbac` | Role-based access control, permissions, middleware |
| `tenant` | Tenant management, settings, plan enforcement |
| `repository` | Repository CRUD, status management |
| `ingestion` | Repository ingestion pipeline, chunking, embedding |
| `rag` | RAG retrieval, hybrid search, reranking, citations |
| `chat` | Chat service, session management, streaming |
| `agents` | Agent base class, orchestration, findings |
| `arch-agent` | Architecture agent |
| `cr-agent` | Code review agent |
| `bug-agent` | Bug detection agent |
| `sec-agent` | Security agent |
| `doc-agent` | Documentation agent |
| `test-agent` | Test generation agent |
| `issue-agent` | Issue generation agent |
| `refactor-agent` | Refactoring agent |
| `github` | GitHub integration, webhooks, PR review, Issues push |
| `dashboard` | Repository metrics and AI analytics dashboards |
| `observability` | Logging, tracing, metrics, alerting |
| `ci` | GitHub Actions workflows |
| `k8s` | Kubernetes manifests, Helm charts |
| `deploy` | Deployment configuration, NGINX, secrets |
| `hardening` | Performance tuning, security hardening |
| `frontend` | Vue SPA — used when scope is cross-cutting |

### Example Commit Sequence (Phase 3 — Database Layer)

```
chore(scaffold): add pyproject.toml with all pinned backend dependencies
feat(db): add SQLAlchemy async session factory with write/read routing
feat(db): add domain entities — Tenant, User, Repository, AnalysisJob, AgentFinding
feat(db): add domain repository interfaces (abstract base classes)
feat(db): add ORM models for auth and RBAC tables (users, roles, permissions, user_roles, refresh_tokens)
feat(db): add ORM models for tenant management tables
feat(db): add ORM models for repository management tables
feat(db): add ORM models for analysis and agent tables with partitioning on agent_findings
feat(db): add ORM models for RAG metadata, chat, GitHub integration, dashboard, and audit tables
migration(db): 001_initial_schema — full schema with indexes, FK constraints, and partitioned tables
feat(db): add repository base class with mandatory tenant_id filter injection
feat(db): add concrete repository implementations for all domain interfaces
test(db): add unit tests — verify tenant_id filter present on all repository read/update/delete operations
test(db): add integration tests — verify cross-tenant isolation via API for all entity types
```

### Branch Strategy

```
main                    — production-ready; protected; squash merge only
  └── staging           — auto-deployed to staging on merge from main
  └── phase/1-scaffold
  └── phase/3-database-layer
  └── phase/4a-auth-rbac
  └── phase/4b-frontend-scaffold
  └── feat/cr-agent-pr-comment-posting
  └── fix/auth-refresh-token-rotation
  └── security/zip-extraction-sandbox
  └── migration/002-add-analysis-scope-index
```

**Pull Request requirements before merge:**
- All CI checks pass (lint, type-check, unit tests, integration tests, dependency scan).
- At least one reviewer approval.
- No unresolved comments.
- Branch is up-to-date with `main`.
- For migrations: a second reviewer with database expertise must approve.
- For security-scoped changes: security review must be noted in the PR description.

---

*End of Implementation Roadmap*

---

*This roadmap is derived exclusively from PRD v1.0, Architecture v1.0, Database v1.0, and API v1.0. It defines the implementation order required to build the platform as specified. It does not redesign, simplify, or remove any feature, agent, or architectural component defined in those source documents. All significant sequencing changes must be reviewed against the dependency map in Section 3 before work is rescheduled.*
