# API Specification

# AI-Powered Developer Copilot Platform

---

| Field             | Detail                                      |
|-------------------|---------------------------------------------|
| Document Version  | 1.0                                         |
| Status            | Draft                                       |
| Product Name      | AI-Powered Developer Copilot Platform       |
| Document Type     | API Contract Specification                  |
| Source Documents  | PRD v1.0, Architecture v1.0, Database v1.0  |
| Last Updated      | June 2025                                   |
| Classification    | Internal — Confidential                     |

---

## Table of Contents

1. API Overview
2. API Design Principles
3. Authentication & Authorization
4. API Versioning Strategy
5. Error Handling Standards
6. Pagination Standards
7. Rate Limiting Strategy
8. Repository Management APIs
9. Repository Analysis APIs
10. Repository-Aware Chat APIs
11. RAG Retrieval APIs
12. Analysis Job APIs
13. Agent Execution APIs
14. Agent Findings APIs
15. Architecture Agent APIs
16. Code Review Agent APIs
17. Bug Detection Agent APIs
18. Security Agent APIs
19. Documentation Agent APIs
20. Test Generation Agent APIs
21. Issue Generation Agent APIs
22. Refactoring Agent APIs
23. GitHub Integration APIs
24. Dashboard APIs
25. Analytics APIs
26. User Management APIs
27. Tenant Management APIs
28. Audit Log APIs
29. Webhook APIs
30. Internal Service APIs
31. API Lifecycle Flows

---

## 1. API Overview

The AI-Powered Developer Copilot Platform exposes a RESTful HTTP API built on FastAPI. All endpoints are served under the versioned base path `/api/v1/`. Streaming responses (chat) use Server-Sent Events (SSE). Long-running operations (indexing, analysis, agent execution) return job reference IDs immediately; callers poll a status endpoint or subscribe to SSE for progress updates.

**Base URL:** `https://{host}/api/v1`

**Content Type:** `application/json` for all request and response bodies unless noted (multipart for file uploads).

**Streaming:** Chat endpoints return `text/event-stream`.

**Tenant Isolation:** Every request is scoped to the tenant derived from the authenticated user's JWT. No cross-tenant access is possible at the API layer.

**Async-First:** All endpoints are implemented as `async def` handlers in FastAPI. Background operations (indexing, analysis) are dispatched to Celery workers and never block the request cycle.

---

## 2. API Design Principles

**Thin Route Handlers:** Route handlers validate input via Pydantic schemas, call the appropriate application service, and return the response. No business logic lives in handlers.

**Strict Input Validation:** All request bodies are validated with Pydantic v2 models. Field-level constraints (min/max length, regex, enum membership) are enforced before reaching the service layer. Validation failures return `422 Unprocessable Entity` with field-level error detail.

**Consistent Response Envelopes:** All successful responses follow a consistent structure. Collections are paginated. Single-resource responses return the resource object directly.

**Idempotent Operations:** All `PUT` endpoints are fully idempotent. `POST` endpoints that may be retried (e.g., triggering analysis) use client-supplied idempotency keys where noted.

**RBAC at Every Endpoint:** Every endpoint declares the minimum required permission. The RBAC middleware enforces this before the handler is invoked. Permission checks use the tenant-scoped role and repository-level access grants.

**Structured Errors:** All errors follow the standard error schema (see Section 5). HTTP status codes map to machine-readable error codes.

**No Business Logic in Schemas:** Pydantic request/response schemas are pure data contracts. Computed fields or cross-field logic belongs in the service layer.

---

## 3. Authentication & Authorization

### 3.1 Authentication Mechanism

The platform uses JWT (JSON Web Tokens) with short-lived access tokens and rotating refresh tokens.

| Token Type    | Lifetime | Storage             | Notes                                              |
|---------------|----------|---------------------|----------------------------------------------------|
| Access Token  | 15 min   | Memory / HTTP header| Never persisted server-side; validated via signature |
| Refresh Token | 7 days   | HTTP-only cookie    | Stored hashed in `refresh_tokens` table; rotated on every use |

**Access Token Claims:**

```json
{
  "sub": "<user_id>",
  "tenant_id": "<tenant_id>",
  "email": "user@example.com",
  "role": "admin",
  "permissions": ["repository:upload", "analysis:trigger_full", "..."],
  "iat": 1719000000,
  "exp": 1719000900
}
```

All API requests (except `/auth/login`, `/auth/refresh`, `/webhooks/*`) must include the access token as a `Bearer` token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### 3.2 Authentication Endpoints

#### POST /auth/register

**Purpose:** Register a new user and create a new tenant (organization) in a single operation.

**Auth Required:** No

**Rate Limit:** 10 req/min per IP

**Request Schema:**

```json
{
  "email": "string (required, valid email, max 320 chars)",
  "password": "string (required, min 8 chars, max 128 chars)",
  "display_name": "string (required, max 255 chars)",
  "organization_name": "string (required, max 255 chars)",
  "organization_slug": "string (required, 3-100 chars, lowercase alphanumeric + hyphen)"
}
```

**Response Schema (201 Created):**

```json
{
  "user_id": "uuid",
  "tenant_id": "uuid",
  "email": "string",
  "display_name": "string",
  "organization_slug": "string",
  "access_token": "string",
  "token_type": "bearer"
}
```

**Error Responses:** `400` slug already taken, `409` email already registered, `422` validation error.

---

#### POST /auth/login

**Purpose:** Authenticate an existing user and issue access + refresh tokens.

**Auth Required:** No

**Rate Limit:** 20 req/min per IP; lockout enforced after 5 consecutive failures (stored in `users.locked_until`).

**Request Schema:**

```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

**Response Schema (200 OK):**

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "string",
    "display_name": "string",
    "role": "admin | team_lead | developer",
    "tenant_id": "uuid"
  }
}
```

Refresh token is set as an HTTP-only `Set-Cookie` header: `refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh`.

**Error Responses:** `401` invalid credentials, `403` account locked, `403` email not verified.

---

#### POST /auth/refresh

**Purpose:** Exchange a valid refresh token for a new access token + rotated refresh token.

**Auth Required:** HTTP-only refresh token cookie.

**Rate Limit:** 60 req/min per user.

**Request Schema:** No body. Refresh token read from cookie.

**Response Schema (200 OK):**

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Error Responses:** `401` token expired or revoked, `401` token reuse detected (family revoked).

---

#### POST /auth/logout

**Purpose:** Revoke the current refresh token.

**Auth Required:** Bearer token.

**Response:** `204 No Content`

---

#### POST /auth/github/callback

**Purpose:** Complete GitHub OAuth flow and issue platform tokens for the authenticated GitHub user.

**Auth Required:** No

**Request Schema:**

```json
{
  "code": "string (OAuth authorization code from GitHub)",
  "state": "string (CSRF state token)",
  "tenant_slug": "string (target organization)"
}
```

**Response Schema (200 OK):** Same as `/auth/login` response.

**Error Responses:** `400` invalid state, `401` GitHub OAuth error.

---

### 3.3 Permission Reference

| Permission                  | Admin | Team Lead | Developer |
|-----------------------------|-------|-----------|-----------|
| `repository:upload`         | ✅    | ✅        | ❌        |
| `repository:delete`         | ✅    | ❌        | ❌        |
| `repository:read`           | ✅    | ✅        | ✅        |
| `analysis:trigger_full`     | ✅    | ✅        | ❌        |
| `analysis:trigger_pr`       | ✅    | ✅        | ✅        |
| `analysis:read`             | ✅    | ✅        | ✅        |
| `chat:use`                  | ✅    | ✅        | ✅        |
| `agent:invoke`              | ✅    | ✅        | ✅        |
| `finding:update_status`     | ✅    | ✅        | ✅        |
| `github:manage`             | ✅    | ❌        | ❌        |
| `dashboard:read`            | ✅    | ✅        | ❌        |
| `user:manage`               | ✅    | ❌        | ❌        |
| `tenant:manage`             | ✅    | ❌        | ❌        |
| `audit_log:read`            | ✅    | ❌        | ❌        |
| `settings:manage`           | ✅    | ❌        | ❌        |

---

## 4. API Versioning Strategy

All endpoints are prefixed with `/api/v1/`. The major version is incremented only for breaking changes. Non-breaking additions (new fields, new optional parameters) are made without a version bump and documented in the changelog.

**Version Lifecycle:**

- `v1` — Current stable version.
- When `v2` is introduced, `v1` is supported for a minimum of 12 months with a deprecation notice in all `v1` response headers: `Deprecation: true`, `Sunset: <RFC 7231 date>`.

**Version Header:** Clients may optionally pin to a minor revision via `API-Version: 2025-06` (date-based). Without this header, the latest stable revision of `v1` is used.

---

## 5. Error Handling Standards

All error responses conform to the following envelope:

```json
{
  "error": {
    "code": "string (machine-readable snake_case code)",
    "message": "string (human-readable description)",
    "details": [
      {
        "field": "string (for validation errors)",
        "issue": "string"
      }
    ],
    "request_id": "string (UUID, correlates with server logs)"
  }
}
```

**HTTP Status Code Mapping:**

| Status | Code                        | Meaning                                          |
|--------|-----------------------------|--------------------------------------------------|
| 400    | `bad_request`               | Malformed request body or parameters             |
| 401    | `unauthorized`              | Missing or invalid access token                  |
| 403    | `forbidden`                 | Authenticated but insufficient permissions       |
| 404    | `not_found`                 | Resource does not exist within tenant scope      |
| 409    | `conflict`                  | Unique constraint violation or state conflict    |
| 413    | `payload_too_large`         | Upload exceeds size limit                        |
| 422    | `validation_error`          | Pydantic schema validation failure               |
| 429    | `rate_limit_exceeded`       | Rate limit hit; `Retry-After` header included    |
| 500    | `internal_error`            | Unhandled server error                           |
| 503    | `service_unavailable`       | Background service (Celery/Qdrant) unavailable   |

---

## 6. Pagination Standards

All collection endpoints support cursor-based pagination.

**Query Parameters:**

| Parameter | Type    | Default | Description                             |
|-----------|---------|---------|-----------------------------------------|
| `cursor`  | string  | null    | Opaque cursor from previous response    |
| `limit`   | integer | 20      | Records per page; max 100               |
| `sort`    | string  | varies  | Field to sort by (endpoint-documented)  |
| `order`   | string  | `desc`  | `asc` or `desc`                         |

**Paginated Response Envelope:**

```json
{
  "items": [...],
  "pagination": {
    "cursor": "string (next page cursor, null if last page)",
    "has_more": true,
    "total": 342
  }
}
```

---

## 7. Rate Limiting Strategy

Rate limits are enforced per user per endpoint group using a sliding window counter stored in Redis. Limits are configurable per tenant via `tenant_settings.api_rate_limit_per_min` (default: 60 req/min).

**Response Headers (all endpoints):**

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1719000060
```

**Endpoint-Specific Limits:**

| Endpoint Group             | Default Limit    | Notes                                    |
|----------------------------|------------------|------------------------------------------|
| `POST /auth/login`         | 20 req/min/IP    | Stricter; lockout after 5 failures       |
| `POST /auth/register`      | 10 req/min/IP    | IP-based only                            |
| `POST /repositories/upload`| 5 req/min/tenant | Enforced on upload endpoint              |
| `POST /analysis/`          | 10 req/min/tenant| Analysis trigger rate                    |
| `POST /chat/sessions/*/messages` | 30 req/min/user | Per session message rate            |
| `POST /rag/retrieve`       | 60 req/min/user  | RAG retrieval                            |
| `GET /webhooks/*`          | 500 req/min/IP   | GitHub webhook receiver; higher limit    |
| All other endpoints        | Tenant setting   | Default 60 req/min per user              |

When a rate limit is exceeded, the API returns `429 Too Many Requests` with a `Retry-After: <seconds>` header.

---

## 8. Repository Management APIs

### POST /repositories/upload

**Purpose:** Upload a ZIP archive containing a source code repository for indexing. Triggers the repository processing pipeline asynchronously.

**Auth Required:** Bearer token. **Permission:** `repository:upload`

**Rate Limit:** 5 req/min per tenant.

**Content-Type:** `multipart/form-data`

**Request Fields:**

| Field         | Type   | Required | Description                                         |
|---------------|--------|----------|-----------------------------------------------------|
| `file`        | binary | Yes      | ZIP archive, max 2 GB                               |
| `name`        | string | Yes      | Display name for the repository (max 255 chars)     |
| `description` | string | No       | Optional description (max 1000 chars)               |

**Response Schema (202 Accepted):**

```json
{
  "repository_id": "uuid",
  "name": "string",
  "source_type": "zip",
  "index_status": "pending",
  "created_at": "ISO8601",
  "index_run_id": "uuid"
}
```

**Error Responses:** `400` invalid ZIP, `413` file too large, `403` repo limit reached for tenant plan, `422` validation error.

---

### POST /repositories/connect/github

**Purpose:** Connect a GitHub repository to the platform. Validates the GitHub installation has access and triggers initial indexing.

**Auth Required:** Bearer token. **Permission:** `repository:upload`

**Request Schema:**

```json
{
  "github_repository_id": "integer (GitHub numeric repo ID)",
  "installation_id": "uuid (platform GitHub installation record ID)",
  "name": "string (display name, max 255 chars)",
  "description": "string (optional)"
}
```

**Response Schema (202 Accepted):** Same structure as `/repositories/upload` with `source_type: "github"`.

**Error Responses:** `400` installation not found, `403` GitHub App lacks access to repo, `409` repository already connected.

---

### GET /repositories

**Purpose:** List all repositories accessible to the authenticated user within the tenant.

**Auth Required:** Bearer token. **Permission:** `repository:read`

**Query Parameters:** `cursor`, `limit`, `sort` (`created_at` | `name` | `last_indexed_at`), `order`, `status` (filter by `index_status`), `search` (name substring).

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string | null",
      "source_type": "zip | github",
      "index_status": "pending | indexing | ready | error | stale",
      "primary_language": "string | null",
      "detected_languages": ["string"],
      "total_files": "integer | null",
      "total_lines_of_code": "integer | null",
      "total_chunks": "integer | null",
      "last_indexed_at": "ISO8601 | null",
      "last_analysis_at": "ISO8601 | null",
      "default_branch": "string | null",
      "created_by": "uuid",
      "created_at": "ISO8601"
    }
  ],
  "pagination": { "cursor": "string | null", "has_more": false, "total": 12 }
}
```

---

### GET /repositories/{repository_id}

**Purpose:** Retrieve full metadata for a single repository.

**Auth Required:** Bearer token. **Permission:** `repository:read` + repository access check.

**Path Parameter:** `repository_id` (UUID)

**Response Schema (200 OK):** Full repository object (same fields as list item) plus `index_error_message: string | null`, `storage_path_prefix: string`, `is_active: boolean`.

**Error Responses:** `404` not found or not accessible to user.

---

### PUT /repositories/{repository_id}

**Purpose:** Update repository metadata (name, description).

**Auth Required:** Bearer token. **Permission:** `repository:upload`

**Request Schema:**

```json
{
  "name": "string (optional, max 255 chars)",
  "description": "string (optional, max 1000 chars)"
}
```

**Response Schema (200 OK):** Updated repository object.

---

### DELETE /repositories/{repository_id}

**Purpose:** Soft-delete a repository and schedule async deletion of all associated data (Qdrant vectors, analysis jobs, findings, chat sessions, GitHub links) within 24 hours.

**Auth Required:** Bearer token. **Permission:** `repository:delete`

**Response:** `204 No Content`

**Error Responses:** `403` insufficient permissions, `404` not found.

---

### GET /repositories/{repository_id}/index-runs

**Purpose:** List the indexing history for a repository.

**Auth Required:** Bearer token. **Permission:** `repository:read`

**Query Parameters:** `cursor`, `limit`, `status` filter.

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "id": "uuid",
      "trigger": "manual | github_push | initial | scheduled",
      "index_type": "full | incremental",
      "status": "running | completed | failed | cancelled",
      "started_at": "ISO8601",
      "completed_at": "ISO8601 | null",
      "files_processed": "integer | null",
      "files_skipped": "integer | null",
      "chunks_created": "integer | null",
      "chunks_updated": "integer | null",
      "chunks_deleted": "integer | null",
      "git_commit_sha": "string | null",
      "error_message": "string | null"
    }
  ],
  "pagination": { "cursor": "string | null", "has_more": false, "total": 5 }
}
```

---

### POST /repositories/{repository_id}/reindex

**Purpose:** Manually trigger a full re-index of the repository.

**Auth Required:** Bearer token. **Permission:** `analysis:trigger_full`

**Request Schema:** No body required. Optional JSON body:

```json
{
  "index_type": "full | incremental (default: full)"
}
```

**Response Schema (202 Accepted):**

```json
{
  "index_run_id": "uuid",
  "status": "running"
}
```

---

## 9. Repository Analysis APIs

### POST /repositories/{repository_id}/analysis

**Purpose:** Trigger a new analysis job for the repository. Dispatches all enabled agents concurrently via Celery.

**Auth Required:** Bearer token. **Permission:** `analysis:trigger_full`

**Request Schema:**

```json
{
  "analysis_type": "full | incremental | pr (required)",
  "scope": {
    "type": "full | pr | file | directory",
    "pr_number": "integer (required when type=pr)",
    "file_paths": ["string (for type=file)"],
    "directory_path": "string (for type=directory)",
    "git_commit_sha": "string (optional; defaults to HEAD)"
  },
  "agents": ["architecture", "code_review", "bug_detection", "security",
             "documentation", "test_generation", "issue_generation", "refactoring"],
  "idempotency_key": "string (optional; prevents duplicate triggers)"
}
```

**Response Schema (202 Accepted):**

```json
{
  "analysis_job_id": "uuid",
  "status": "pending",
  "analysis_type": "full",
  "agents_dispatched": ["architecture", "code_review", "..."],
  "created_at": "ISO8601"
}
```

**Error Responses:** `400` invalid scope, `409` analysis already running for repo (if no idempotency key), `422` validation error.

---

### GET /repositories/{repository_id}/analysis

**Purpose:** List analysis jobs for a repository.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Query Parameters:** `cursor`, `limit`, `status`, `analysis_type`, `sort` (`created_at`).

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "id": "uuid",
      "trigger": "manual | github_push | github_pr | scheduled | post_index",
      "analysis_type": "full | incremental | pr",
      "status": "pending | running | completed | partial | failed",
      "total_findings": "integer | null",
      "critical_findings": "integer | null",
      "high_findings": "integer | null",
      "composite_health_score": "number | null",
      "git_commit_sha": "string | null",
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null",
      "created_at": "ISO8601"
    }
  ],
  "pagination": { "cursor": "string | null", "has_more": false, "total": 20 }
}
```

---

## 10. Repository-Aware Chat APIs

### POST /chat/sessions

**Purpose:** Create a new chat session scoped to one or more repositories.

**Auth Required:** Bearer token. **Permission:** `chat:use`

**Request Schema:**

```json
{
  "repository_ids": ["uuid (at least one required)"],
  "title": "string (optional, max 255 chars)",
  "scope": {
    "type": "repository | directory | file",
    "path": "string (optional; file or directory path for narrowed scope)"
  }
}
```

**Response Schema (201 Created):**

```json
{
  "session_id": "uuid",
  "repository_ids": ["uuid"],
  "scope": { "type": "repository", "path": null },
  "title": "string | null",
  "created_at": "ISO8601",
  "message_count": 0
}
```

---

### GET /chat/sessions

**Purpose:** List the authenticated user's chat sessions.

**Auth Required:** Bearer token. **Permission:** `chat:use`

**Query Parameters:** `cursor`, `limit`, `repository_id` (filter).

**Response Schema (200 OK):** Paginated list of session objects (same fields as create response).

---

### GET /chat/sessions/{session_id}

**Purpose:** Retrieve session metadata and message history.

**Auth Required:** Bearer token. **Permission:** `chat:use` + session ownership check.

**Query Parameters:** `cursor`, `limit` (for message pagination), `order` (`asc` | `desc`).

**Response Schema (200 OK):**

```json
{
  "session_id": "uuid",
  "repository_ids": ["uuid"],
  "scope": { "type": "string", "path": "string | null" },
  "title": "string | null",
  "messages": [
    {
      "id": "uuid",
      "role": "user | assistant",
      "content": "string",
      "sequence_number": 1,
      "citations": [
        {
          "file_path": "string",
          "line_start": "integer",
          "line_end": "integer",
          "repository_id": "uuid",
          "chunk_id": "uuid"
        }
      ],
      "created_at": "ISO8601"
    }
  ],
  "pagination": { "cursor": "string | null", "has_more": false, "total": 15 }
}
```

---

### POST /chat/sessions/{session_id}/messages

**Purpose:** Send a user message to a chat session and receive a streamed AI response grounded in the repository RAG index.

**Auth Required:** Bearer token. **Permission:** `chat:use`

**Rate Limit:** 30 req/min per user.

**Content-Type (Request):** `application/json`

**Accept (Response):** `text/event-stream`

**Request Schema:**

```json
{
  "content": "string (required, max 10000 chars)",
  "scope_override": {
    "type": "repository | directory | file",
    "path": "string (optional)"
  }
}
```

**SSE Event Stream Format:**

```
event: token
data: {"token": "Based on", "sequence": 1}

event: token
data: {"token": " the auth module...", "sequence": 2}

event: citation
data: {"file_path": "src/auth/login.py", "line_start": 42, "line_end": 58, "repository_id": "uuid", "chunk_id": "uuid"}

event: complete
data: {"message_id": "uuid", "token_count": 312, "rag_sources_count": 4}

event: error
data: {"code": "rag_retrieval_failed", "message": "..."}
```

**Error Responses:** `404` session not found, `403` session not owned by user, `422` content too long, `429` rate limit exceeded.

---

### PUT /chat/sessions/{session_id}/scope

**Purpose:** Update the active scope of a session without resetting history.

**Auth Required:** Bearer token. **Permission:** `chat:use` + session ownership.

**Request Schema:**

```json
{
  "scope": {
    "type": "repository | directory | file",
    "path": "string | null"
  }
}
```

**Response Schema (200 OK):** Updated session object.

---

### DELETE /chat/sessions/{session_id}

**Purpose:** Delete a chat session and its message history.

**Auth Required:** Bearer token. **Permission:** `chat:use` + session ownership.

**Response:** `204 No Content`

---

### POST /chat/sessions/{session_id}/messages/{message_id}/feedback

**Purpose:** Submit user feedback on an AI-generated message (thumbs up/down or incorrect response report).

**Auth Required:** Bearer token. **Permission:** `chat:use`

**Request Schema:**

```json
{
  "feedback_type": "positive | negative | incorrect",
  "comment": "string (optional)"
}
```

**Response:** `204 No Content`

---

## 11. RAG Retrieval APIs

### POST /rag/retrieve

**Purpose:** Direct RAG retrieval endpoint. Returns ranked relevant chunks for a query. Used by agents and direct tooling integrations.

**Auth Required:** Bearer token. **Permission:** `repository:read`

**Rate Limit:** 60 req/min per user.

**Request Schema:**

```json
{
  "query": "string (required, max 2000 chars)",
  "repository_ids": ["uuid (required, at least one)"],
  "scope": {
    "type": "repository | directory | file",
    "path": "string | null"
  },
  "top_k": "integer (default: 10, max: 50)",
  "similarity_threshold": "number (0.0–1.0, default: 0.7)",
  "retrieval_mode": "hybrid | dense | sparse (default: hybrid)"
}
```

**Response Schema (200 OK):**

```json
{
  "query": "string",
  "chunks": [
    {
      "chunk_id": "uuid",
      "repository_id": "uuid",
      "file_path": "string",
      "line_start": "integer",
      "line_end": "integer",
      "language": "string",
      "chunk_type": "function | class | file | paragraph | config",
      "content": "string",
      "relevance_score": 0.923,
      "retrieval_rank": 1
    }
  ],
  "retrieval_time_ms": 124
}
```

**Error Responses:** `400` invalid repository IDs, `403` RBAC violation (user lacks access to specified repositories), `422` validation error.

---

### GET /rag/repositories/{repository_id}/index-status

**Purpose:** Check the RAG index status, freshness, and size metrics for a repository.

**Auth Required:** Bearer token. **Permission:** `repository:read`

**Response Schema (200 OK):**

```json
{
  "repository_id": "uuid",
  "index_status": "pending | indexing | ready | error | stale",
  "total_chunks": "integer | null",
  "last_indexed_at": "ISO8601 | null",
  "index_freshness_minutes": "integer | null",
  "qdrant_collection": "string"
}
```

---

## 12. Analysis Job APIs

### GET /analysis/{analysis_job_id}

**Purpose:** Retrieve the full state of an analysis job including per-agent run status.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "id": "uuid",
  "repository_id": "uuid",
  "trigger": "manual | github_push | github_pr | scheduled | post_index",
  "analysis_type": "full | incremental | pr",
  "status": "pending | running | completed | partial | failed",
  "scope": { "type": "string", "pr_number": "integer | null", "diff_files": ["string"] },
  "total_findings": "integer | null",
  "critical_findings": "integer | null",
  "high_findings": "integer | null",
  "composite_health_score": "number | null",
  "git_commit_sha": "string | null",
  "started_at": "ISO8601 | null",
  "completed_at": "ISO8601 | null",
  "created_at": "ISO8601",
  "agent_runs": [
    {
      "id": "uuid",
      "agent_type": "architecture | code_review | bug_detection | security | documentation | test_generation | issue_generation | refactoring",
      "status": "pending | running | completed | failed | skipped",
      "started_at": "ISO8601 | null",
      "completed_at": "ISO8601 | null",
      "duration_ms": "integer | null",
      "findings_count": "integer | null",
      "rag_queries_count": "integer | null",
      "llm_tokens_used": "integer | null",
      "retry_count": 0,
      "error_message": "string | null"
    }
  ]
}
```

---

### GET /analysis/{analysis_job_id}/stream

**Purpose:** SSE stream for real-time analysis job progress.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Accept:** `text/event-stream`

**SSE Events:**

```
event: agent_started
data: {"agent_type": "security", "agent_run_id": "uuid", "timestamp": "ISO8601"}

event: agent_completed
data: {"agent_type": "security", "agent_run_id": "uuid", "findings_count": 7, "duration_ms": 4200}

event: agent_failed
data: {"agent_type": "documentation", "agent_run_id": "uuid", "error_message": "string"}

event: job_completed
data: {"analysis_job_id": "uuid", "status": "completed", "total_findings": 23, "composite_health_score": 74.5}
```

---

### DELETE /analysis/{analysis_job_id}

**Purpose:** Cancel a running analysis job.

**Auth Required:** Bearer token. **Permission:** `analysis:trigger_full`

**Response:** `204 No Content`

**Error Responses:** `400` job already completed.

---

## 13. Agent Execution APIs

### POST /agents/invoke

**Purpose:** Directly invoke a single agent on a repository or scoped target, independent of a full analysis run.

**Auth Required:** Bearer token. **Permission:** `agent:invoke`

**Request Schema:**

```json
{
  "agent_type": "architecture | code_review | bug_detection | security | documentation | test_generation | issue_generation | refactoring (required)",
  "repository_id": "uuid (required)",
  "scope": {
    "type": "repository | directory | file | diff",
    "path": "string | null",
    "diff_content": "string | null (raw unified diff, for ad-hoc review)"
  },
  "config_overrides": {
    "severity_threshold": "critical | high | medium | low | informational",
    "max_findings": "integer (default: 100)"
  },
  "idempotency_key": "string (optional)"
}
```

**Response Schema (202 Accepted):**

```json
{
  "agent_run_id": "uuid",
  "analysis_job_id": "uuid (auto-created wrapper job)",
  "agent_type": "string",
  "status": "pending",
  "created_at": "ISO8601"
}
```

---

### GET /agents/runs/{agent_run_id}

**Purpose:** Retrieve the current state and result summary of a single agent run.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):** Agent run object (same structure as within `GET /analysis/{id}` → `agent_runs[]`) plus `findings_summary: { critical: 0, high: 2, medium: 5, low: 3, informational: 1 }`.

---

## 14. Agent Findings APIs

### GET /repositories/{repository_id}/findings

**Purpose:** List all open findings for a repository, optionally filtered by agent, severity, status, or file path.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Query Parameters:**

| Parameter        | Type   | Description                                            |
|------------------|--------|--------------------------------------------------------|
| `agent_type`     | string | Filter by agent: `security`, `bug_detection`, etc.     |
| `severity`       | string | Filter: `critical`, `high`, `medium`, `low`, `informational` |
| `status`         | string | Filter: `open`, `resolved`, `false_positive`, `accepted_risk` |
| `file_path`      | string | Substring filter on file path                          |
| `category`       | string | Finding category (e.g., `sql_injection`)               |
| `is_new`         | bool   | Only findings introduced in latest analysis run        |
| `cursor`, `limit`, `sort` (`severity`, `created_at`, `confidence_score`), `order` | | |

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "id": "uuid",
      "agent_type": "string",
      "title": "string",
      "description": "string",
      "category": "string",
      "severity": "critical | high | medium | low | informational",
      "confidence_score": 87,
      "file_path": "string",
      "line_start": "integer | null",
      "line_end": "integer | null",
      "function_name": "string | null",
      "class_name": "string | null",
      "remediation": "string | null",
      "remediation_code": "string | null",
      "cwe_id": "string | null",
      "owasp_category": "string | null",
      "status": "open | resolved | false_positive | accepted_risk",
      "is_new": true,
      "fingerprint": "string",
      "agent_run_id": "uuid",
      "created_at": "ISO8601"
    }
  ],
  "pagination": { "cursor": "string | null", "has_more": false, "total": 47 }
}
```

---

### GET /findings/{finding_id}

**Purpose:** Retrieve full detail for a single finding including RAG sources that informed it.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):** Full finding object (all fields from list) plus:

```json
{
  "rag_sources": [
    {
      "chunk_id": "uuid",
      "file_path": "string",
      "line_start": "integer",
      "line_end": "integer",
      "relevance_score": 0.91,
      "retrieval_rank": 1,
      "content_excerpt": "string (first 500 chars of chunk)"
    }
  ],
  "analysis_job_id": "uuid",
  "resolved_at": "ISO8601 | null",
  "resolved_by": "uuid | null"
}
```

---

### PATCH /findings/{finding_id}/status

**Purpose:** Update the status of a finding (resolve, mark as false positive, accept risk).

**Auth Required:** Bearer token. **Permission:** `finding:update_status`

**Request Schema:**

```json
{
  "status": "resolved | false_positive | accepted_risk (required)",
  "comment": "string (optional)"
}
```

**Response Schema (200 OK):** Updated finding object.

---

### POST /findings/{finding_id}/feedback

**Purpose:** Submit user feedback on a finding (accepted, rejected, false positive). Logged for model improvement.

**Auth Required:** Bearer token. **Permission:** `finding:update_status`

**Request Schema:**

```json
{
  "feedback_type": "accepted | rejected | false_positive | accepted_risk (required)",
  "comment": "string (optional)"
}
```

**Response:** `204 No Content`

**Error Responses:** `409` feedback already submitted by this user for this finding.

---

### GET /repositories/{repository_id}/findings/export

**Purpose:** Export all open findings for a repository as CSV or JSON.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Query Parameters:** `format` (`csv` | `json`, default `json`), all standard filter params.

**Response:** File download with `Content-Disposition: attachment; filename="findings-{repo_name}-{date}.{format}"`.

---

## 15. Architecture Agent APIs

### GET /repositories/{repository_id}/agents/architecture/latest

**Purpose:** Retrieve the most recent completed Architecture Agent output for the repository.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "agent_run_id": "uuid",
  "analysis_job_id": "uuid",
  "completed_at": "ISO8601",
  "architecture_health_score": 68.5,
  "dependency_map_summary": {
    "total_modules": 24,
    "circular_dependency_count": 2,
    "highly_coupled_modules": ["src/core/god_service.py"]
  },
  "findings": [ "...finding objects..." ],
  "findings_summary": { "critical": 1, "high": 3, "medium": 8, "low": 5, "informational": 2 }
}
```

---

## 16. Code Review Agent APIs

### GET /repositories/{repository_id}/agents/code-review/latest

**Purpose:** Retrieve the most recent Code Review Agent output.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "agent_run_id": "uuid",
  "analysis_job_id": "uuid",
  "completed_at": "ISO8601",
  "review_verdict": "approve | request_changes | informational",
  "files_reviewed": 42,
  "findings": [ "...finding objects..." ],
  "findings_summary": { "critical": 0, "high": 2, "medium": 11, "low": 14, "informational": 6 }
}
```

---

### GET /analysis/{analysis_job_id}/agents/code-review/pr-comments

**Purpose:** Retrieve the formatted PR comments produced by the Code Review Agent for a PR-scoped analysis job.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "pr_number": "integer",
  "summary_comment": "string (markdown)",
  "review_verdict": "approve | request_changes | informational",
  "inline_comments": [
    {
      "file_path": "string",
      "line": "integer",
      "side": "RIGHT | LEFT",
      "body": "string (markdown)",
      "severity": "string",
      "finding_id": "uuid"
    }
  ],
  "posted_to_github": true,
  "github_review_id": "integer | null"
}
```

---

## 17. Bug Detection Agent APIs

### GET /repositories/{repository_id}/agents/bug-detection/latest

**Purpose:** Retrieve the most recent Bug Detection Agent output.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "agent_run_id": "uuid",
  "analysis_job_id": "uuid",
  "completed_at": "ISO8601",
  "new_bugs_count": 3,
  "resolved_bugs_count": 1,
  "findings": [ "...finding objects with category: null_dereference | race_condition | unhandled_exception | unchecked_error | ..." ],
  "findings_summary": { "critical": 2, "high": 5, "medium": 9, "low": 4, "informational": 0 }
}
```

---

## 18. Security Agent APIs

### GET /repositories/{repository_id}/agents/security/latest

**Purpose:** Retrieve the most recent Security Agent output.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "agent_run_id": "uuid",
  "analysis_job_id": "uuid",
  "completed_at": "ISO8601",
  "security_health_score": 55.0,
  "exposed_secrets_count": 1,
  "dependency_vulnerabilities_count": 4,
  "owasp_top10_findings": {
    "A01_broken_access_control": 2,
    "A03_injection": 1
  },
  "findings": [ "...finding objects with cwe_id and owasp_category populated..." ],
  "findings_summary": { "critical": 3, "high": 6, "medium": 4, "low": 2, "informational": 1 }
}
```

---

## 19. Documentation Agent APIs

### GET /repositories/{repository_id}/agents/documentation/latest

**Purpose:** Retrieve the most recent Documentation Agent output.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "agent_run_id": "uuid",
  "analysis_job_id": "uuid",
  "completed_at": "ISO8601",
  "documentation_coverage_score": 42.0,
  "undocumented_functions_count": 87,
  "undocumented_classes_count": 12,
  "generated_artifacts": [
    {
      "finding_id": "uuid",
      "artifact_type": "docstring | readme | api_reference",
      "file_path": "string",
      "generated_content": "string (markdown or language-appropriate docstring)"
    }
  ],
  "findings_summary": { "critical": 0, "high": 5, "medium": 22, "low": 60, "informational": 10 }
}
```

---

## 20. Test Generation Agent APIs

### GET /repositories/{repository_id}/agents/test-generation/latest

**Purpose:** Retrieve the most recent Test Generation Agent output.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "agent_run_id": "uuid",
  "analysis_job_id": "uuid",
  "completed_at": "ISO8601",
  "estimated_coverage_increase_pct": 12.5,
  "untested_functions_count": 34,
  "generated_tests": [
    {
      "finding_id": "uuid",
      "target_file_path": "string",
      "target_function": "string",
      "test_framework": "pytest | jest | junit | ...",
      "generated_test_code": "string",
      "test_intent": "string (brief description of what is tested)",
      "edge_cases_covered": ["boundary_null_input", "error_path", "..."]
    }
  ],
  "findings_summary": { "critical": 0, "high": 8, "medium": 19, "low": 7, "informational": 0 }
}
```

---

## 21. Issue Generation Agent APIs

### GET /repositories/{repository_id}/agents/issue-generation/latest

**Purpose:** Retrieve the most recent Issue Generation Agent output.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "agent_run_id": "uuid",
  "analysis_job_id": "uuid",
  "completed_at": "ISO8601",
  "total_issues_generated": 18,
  "issues": [
    {
      "id": "uuid",
      "source_finding_id": "uuid",
      "title": "string",
      "description": "string (markdown)",
      "affected_files": ["string"],
      "severity": "critical | high | medium | low",
      "priority": "P0 | P1 | P2 | P3",
      "category": "string",
      "suggested_assignee": "string | null (GitHub login derived from git blame)",
      "acceptance_criteria": "string",
      "github_issue_id": "integer | null",
      "github_issue_url": "string | null",
      "pushed_at": "ISO8601 | null"
    }
  ]
}
```

---

### POST /repositories/{repository_id}/agents/issue-generation/push-to-github

**Purpose:** Push selected AI-generated issues to the connected GitHub repository's Issues tracker.

**Auth Required:** Bearer token. **Permission:** `github:manage`

**Request Schema:**

```json
{
  "issue_ids": ["uuid (from issue generation output)"],
  "label_mapping": {
    "critical": "priority: critical",
    "high": "priority: high"
  },
  "milestone_id": "integer | null (GitHub milestone ID)"
}
```

**Response Schema (202 Accepted):**

```json
{
  "push_job_id": "uuid",
  "issues_queued": 5,
  "status": "queued"
}
```

**Error Responses:** `400` no GitHub integration configured, `400` issues already pushed.

---

### GET /repositories/{repository_id}/agents/issue-generation/push-jobs/{push_job_id}

**Purpose:** Check the status of a GitHub issue push job.

**Auth Required:** Bearer token. **Permission:** `github:manage`

**Response Schema (200 OK):**

```json
{
  "push_job_id": "uuid",
  "status": "queued | running | completed | failed",
  "issues_pushed": 4,
  "issues_failed": 1,
  "results": [
    {
      "issue_id": "uuid",
      "github_issue_id": "integer | null",
      "github_issue_url": "string | null",
      "error": "string | null"
    }
  ]
}
```

---

## 22. Refactoring Agent APIs

### GET /repositories/{repository_id}/agents/refactoring/latest

**Purpose:** Retrieve the most recent Refactoring Agent output.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Response Schema (200 OK):**

```json
{
  "agent_run_id": "uuid",
  "analysis_job_id": "uuid",
  "completed_at": "ISO8601",
  "technical_debt_score": 38.2,
  "technical_debt_delta": -2.1,
  "refactoring_candidates": [
    {
      "finding_id": "uuid",
      "title": "string",
      "file_path": "string",
      "line_start": "integer",
      "line_end": "integer",
      "issue_type": "duplication | high_complexity | poor_naming | outdated_pattern | mixed_responsibility",
      "estimated_debt_reduction": "number",
      "current_code_excerpt": "string",
      "proposed_refactoring_description": "string",
      "refactored_code_example": "string"
    }
  ],
  "findings_summary": { "critical": 0, "high": 4, "medium": 15, "low": 20, "informational": 5 }
}
```

---

## 23. GitHub Integration APIs

### GET /github/installations

**Purpose:** List all GitHub App installations connected to the tenant.

**Auth Required:** Bearer token. **Permission:** `github:manage`

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "id": "uuid",
      "github_installation_id": "integer",
      "github_account_login": "string",
      "github_account_type": "Organization | User",
      "connected_at": "ISO8601",
      "is_active": true,
      "repository_selection": "all | selected",
      "connected_repositories_count": 12
    }
  ]
}
```

---

### DELETE /github/installations/{installation_id}

**Purpose:** Disconnect a GitHub App installation. Stops webhooks and marks associated repository links as disconnected.

**Auth Required:** Bearer token. **Permission:** `github:manage`

**Response:** `204 No Content`

---

### GET /github/installations/{installation_id}/repositories

**Purpose:** List GitHub repositories accessible via this installation, with sync status.

**Auth Required:** Bearer token. **Permission:** `github:manage`

**Query Parameters:** `cursor`, `limit`, `connected` (bool filter for already-connected repos).

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "github_repo_id": "integer",
      "full_name": "string (org/repo)",
      "private": true,
      "default_branch": "string",
      "connected": false,
      "platform_repository_id": "uuid | null"
    }
  ],
  "pagination": { "cursor": "string | null", "has_more": true, "total": 45 }
}
```

---

### GET /github/repositories/{repository_id}/pr-reviews

**Purpose:** List all automated PR reviews posted by the platform for a connected repository.

**Auth Required:** Bearer token. **Permission:** `analysis:read`

**Query Parameters:** `cursor`, `limit`, `pr_number` (filter), `status`.

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "id": "uuid",
      "pr_number": "integer",
      "pr_title": "string",
      "pr_author_login": "string",
      "analysis_job_id": "uuid",
      "review_verdict": "approve | request_changes | informational",
      "github_review_id": "integer | null",
      "check_run_id": "integer | null",
      "check_status": "success | failure | pending | neutral",
      "critical_findings": "integer",
      "high_findings": "integer",
      "posted_at": "ISO8601 | null",
      "created_at": "ISO8601"
    }
  ],
  "pagination": { "cursor": "string | null", "has_more": false, "total": 31 }
}
```

---

### POST /github/repositories/{repository_id}/pr-reviews/{pr_number}/rerun

**Purpose:** Manually re-trigger a PR review for an existing open pull request.

**Auth Required:** Bearer token. **Permission:** `analysis:trigger_pr`

**Response Schema (202 Accepted):**

```json
{
  "analysis_job_id": "uuid",
  "pr_number": "integer",
  "status": "pending"
}
```

---

## 24. Dashboard APIs

### GET /dashboard/repositories/{repository_id}/health

**Purpose:** Retrieve the current health snapshot and trend data for a repository's Metrics Dashboard.

**Auth Required:** Bearer token. **Permission:** `dashboard:read`

**Query Parameters:** `period` (`7d` | `30d` | `90d`, default `30d`).

**Response Schema (200 OK):**

```json
{
  "repository_id": "uuid",
  "snapshot_at": "ISO8601",
  "composite_health_score": 74.5,
  "scores": {
    "architecture_health": 68.5,
    "security_health": 55.0,
    "documentation_coverage": 42.0,
    "test_coverage_estimate": 61.0,
    "technical_debt_score": 38.2
  },
  "findings_summary": {
    "open_critical": 3,
    "open_high": 11,
    "open_medium": 27,
    "open_low": 18,
    "open_informational": 7
  },
  "trend": [
    {
      "snapshot_at": "ISO8601",
      "composite_health_score": 71.0,
      "open_critical": 5,
      "open_high": 13
    }
  ],
  "code_stats": {
    "total_files": 312,
    "total_lines_of_code": 87400,
    "primary_language": "Python",
    "detected_languages": ["Python", "TypeScript", "SQL"]
  }
}
```

---

### GET /dashboard/overview

**Purpose:** Tenant-wide dashboard overview across all repositories.

**Auth Required:** Bearer token. **Permission:** `dashboard:read`

**Query Parameters:** `period` (`7d` | `30d` | `90d`).

**Response Schema (200 OK):**

```json
{
  "tenant_id": "uuid",
  "repositories_total": 14,
  "repositories_ready": 12,
  "repositories_stale": 2,
  "aggregate_findings": {
    "open_critical": 7,
    "open_high": 34,
    "new_this_period": 12,
    "resolved_this_period": 8
  },
  "average_health_score": 69.2,
  "per_repository": [
    {
      "repository_id": "uuid",
      "name": "string",
      "composite_health_score": "number | null",
      "open_critical": "integer",
      "last_analysis_at": "ISO8601 | null"
    }
  ]
}
```

---

### GET /dashboard/repositories/{repository_id}/health/export

**Purpose:** Export health snapshot data as CSV or JSON.

**Auth Required:** Bearer token. **Permission:** `dashboard:read`

**Query Parameters:** `format` (`csv` | `json`), `period`.

**Response:** File download.

---

## 25. Analytics APIs

### GET /analytics/agents/utilization

**Purpose:** AI agent utilization metrics: runs per agent, average duration, findings per run, false positive rate per agent.

**Auth Required:** Bearer token. **Permission:** `dashboard:read`

**Query Parameters:** `period` (`7d` | `30d` | `90d`), `repository_id` (optional filter).

**Response Schema (200 OK):**

```json
{
  "period": "30d",
  "agents": [
    {
      "agent_type": "string",
      "total_runs": 42,
      "successful_runs": 40,
      "failed_runs": 2,
      "average_duration_ms": 3800,
      "total_findings": 187,
      "false_positive_rate_pct": 8.5,
      "llm_tokens_total": 2400000
    }
  ]
}
```

---

### GET /analytics/findings/trends

**Purpose:** Time-series trend of findings by severity across all or selected repositories.

**Auth Required:** Bearer token. **Permission:** `dashboard:read`

**Query Parameters:** `period`, `repository_id`, `agent_type`, `granularity` (`day` | `week`).

**Response Schema (200 OK):**

```json
{
  "period": "30d",
  "granularity": "day",
  "series": [
    {
      "date": "ISO8601 date",
      "open_critical": 3,
      "open_high": 11,
      "new": 2,
      "resolved": 1
    }
  ]
}
```

---

### GET /analytics/chat/usage

**Purpose:** Chat usage metrics: sessions, messages, response ratings.

**Auth Required:** Bearer token. **Permission:** `dashboard:read`

**Query Parameters:** `period`, `repository_id`.

**Response Schema (200 OK):**

```json
{
  "total_sessions": 214,
  "total_messages_sent": 1847,
  "positive_feedback_rate_pct": 87.2,
  "average_rag_sources_per_response": 4.1,
  "top_queried_repositories": [
    { "repository_id": "uuid", "name": "string", "message_count": 402 }
  ]
}
```

---

## 26. User Management APIs

### GET /users

**Purpose:** List all users in the tenant.

**Auth Required:** Bearer token. **Permission:** `user:manage`

**Query Parameters:** `cursor`, `limit`, `search` (name/email substring), `role`.

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "id": "uuid",
      "email": "string",
      "display_name": "string",
      "auth_provider": "local | github | google",
      "role": "admin | team_lead | developer",
      "is_active": true,
      "is_email_verified": true,
      "last_login_at": "ISO8601 | null",
      "created_at": "ISO8601"
    }
  ],
  "pagination": { "cursor": "string | null", "has_more": false, "total": 8 }
}
```

---

### POST /users

**Purpose:** Invite a new user to the tenant.

**Auth Required:** Bearer token. **Permission:** `user:manage`

**Request Schema:**

```json
{
  "email": "string (required, valid email)",
  "display_name": "string (required)",
  "role": "admin | team_lead | developer (required)"
}
```

**Response Schema (201 Created):** User object as in list response.

**Error Responses:** `409` email already exists in tenant, `403` user limit reached for plan.

---

### GET /users/{user_id}

**Purpose:** Retrieve a single user's profile and role.

**Auth Required:** Bearer token. **Permission:** `user:manage` or self (`sub` == `user_id`).

**Response Schema (200 OK):** Full user object.

---

### PUT /users/{user_id}

**Purpose:** Update a user's display name or role.

**Auth Required:** Bearer token. **Permission:** `user:manage`

**Request Schema:**

```json
{
  "display_name": "string (optional)",
  "role": "admin | team_lead | developer (optional)",
  "is_active": "boolean (optional)"
}
```

**Response Schema (200 OK):** Updated user object.

**Error Responses:** `403` cannot demote the last admin.

---

### DELETE /users/{user_id}

**Purpose:** Soft-delete a user (deactivate account, revoke tokens).

**Auth Required:** Bearer token. **Permission:** `user:manage`

**Response:** `204 No Content`

---

### GET /users/{user_id}/repository-access

**Purpose:** List repository-level access grants for a user.

**Auth Required:** Bearer token. **Permission:** `user:manage`

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "repository_id": "uuid",
      "repository_name": "string",
      "access_level": "read | write",
      "granted_at": "ISO8601",
      "granted_by": "uuid | null"
    }
  ]
}
```

---

### POST /users/{user_id}/repository-access

**Purpose:** Grant a user explicit access to a repository.

**Auth Required:** Bearer token. **Permission:** `user:manage`

**Request Schema:**

```json
{
  "repository_id": "uuid (required)",
  "access_level": "read | write (required)"
}
```

**Response:** `201 Created`

---

### DELETE /users/{user_id}/repository-access/{repository_id}

**Purpose:** Revoke a user's repository-level access.

**Auth Required:** Bearer token. **Permission:** `user:manage`

**Response:** `204 No Content`

---

## 27. Tenant Management APIs

### GET /tenant

**Purpose:** Retrieve the current tenant's profile and plan configuration.

**Auth Required:** Bearer token. **Permission:** Any authenticated user.

**Response Schema (200 OK):**

```json
{
  "id": "uuid",
  "slug": "string",
  "display_name": "string",
  "plan": "free | pro | enterprise",
  "is_active": true,
  "max_repositories": 10,
  "max_users": 5,
  "data_region": "us | eu",
  "current_repository_count": 7,
  "current_user_count": 4,
  "created_at": "ISO8601"
}
```

---

### PUT /tenant

**Purpose:** Update tenant display name.

**Auth Required:** Bearer token. **Permission:** `tenant:manage`

**Request Schema:**

```json
{
  "display_name": "string (required, max 255 chars)"
}
```

**Response Schema (200 OK):** Updated tenant object.

---

### GET /tenant/settings

**Purpose:** Retrieve the tenant's AI agent and platform configuration settings.

**Auth Required:** Bearer token. **Permission:** `settings:manage`

**Response Schema (200 OK):**

```json
{
  "enabled_agents": {
    "architecture": true,
    "code_review": true,
    "bug_detection": true,
    "security": true,
    "documentation": true,
    "test_generation": true,
    "issue_generation": true,
    "refactoring": true
  },
  "severity_thresholds": { "security": "high", "bug_detection": "medium" },
  "pr_review_enabled": true,
  "pr_block_on_critical": false,
  "auto_analysis_on_push": true,
  "auto_analysis_on_pr": true,
  "api_rate_limit_per_min": 60,
  "chat_session_ttl_hours": 24,
  "analysis_retention_days": 365
}
```

---

### PUT /tenant/settings

**Purpose:** Update tenant settings.

**Auth Required:** Bearer token. **Permission:** `settings:manage`

**Request Schema:** Partial update; any subset of the settings fields is accepted.

**Response Schema (200 OK):** Updated settings object.

---

## 28. Audit Log APIs

### GET /audit-logs

**Purpose:** List immutable audit log entries for the tenant.

**Auth Required:** Bearer token. **Permission:** `audit_log:read`

**Query Parameters:**

| Parameter       | Type   | Description                                             |
|-----------------|--------|---------------------------------------------------------|
| `cursor`        | string | Pagination cursor                                       |
| `limit`         | int    | Max 100                                                 |
| `actor_id`      | uuid   | Filter by user who performed the action                 |
| `action`        | string | Filter by action: `repository.uploaded`, `user.role_changed`, etc. |
| `resource_type` | string | `repository`, `user`, `tenant`, `analysis_job`, etc.   |
| `resource_id`   | uuid   | Filter by specific resource                             |
| `from`          | ISO8601| Start of time range                                     |
| `to`            | ISO8601| End of time range                                       |

**Response Schema (200 OK):**

```json
{
  "items": [
    {
      "id": "uuid",
      "occurred_at": "ISO8601",
      "actor_id": "uuid | null",
      "actor_email": "string | null",
      "action": "string",
      "resource_type": "string",
      "resource_id": "uuid | null",
      "ip_address": "string | null",
      "user_agent": "string | null",
      "metadata": {}
    }
  ],
  "pagination": { "cursor": "string | null", "has_more": false, "total": 1240 }
}
```

---

### GET /audit-logs/export

**Purpose:** Export audit logs as CSV.

**Auth Required:** Bearer token. **Permission:** `audit_log:read`

**Query Parameters:** Same filters as list endpoint.

**Response:** CSV file download. Audit logs are retained for a minimum of 90 days per PRD requirement.

---

## 29. Webhook APIs

### POST /webhooks/github

**Purpose:** Receive GitHub App webhook events (push, pull_request, installation). Processed asynchronously by Celery workers.

**Auth Required:** GitHub webhook signature (`X-Hub-Signature-256` header, HMAC-SHA256 of payload).

**Rate Limit:** 500 req/min per IP (NGINX edge limit).

**Content-Type:** `application/json`

**Headers Required:**

```
X-GitHub-Event: push | pull_request | installation | ...
X-GitHub-Delivery: <uuid>
X-Hub-Signature-256: sha256=<hmac>
```

**Response:** `200 OK` with body `{"status": "accepted"}` immediately upon signature validation. Processing happens asynchronously. Duplicate deliveries (same `X-GitHub-Delivery`) are deduplicated via Redis before worker dispatch.

**Error Responses:** `401` invalid signature, `400` unrecognized event type.

**Supported Event Types:**

| GitHub Event       | Platform Action                                          |
|--------------------|----------------------------------------------------------|
| `push`             | Trigger incremental re-index + optional re-analysis      |
| `pull_request` (opened, synchronize, reopened) | Trigger PR-scoped analysis   |
| `installation`     | Create/update `github_installations` record              |
| `installation_repositories` | Sync available repos for installation           |

---

## 30. Internal Service APIs

These endpoints are used internally between platform services or by the Celery worker layer. They are not exposed through NGINX to external clients. Access is enforced by internal network policy and a shared service API key.

### POST /internal/repositories/{repository_id}/index-complete

**Purpose:** Called by the Celery indexing worker to report completion of a repository index run. Updates `repositories.index_status`, publishes `RepositoryIndexed` event.

**Auth:** Internal service key (`X-Internal-Key` header).

**Request Schema:**

```json
{
  "index_run_id": "uuid",
  "status": "completed | failed",
  "files_processed": "integer",
  "files_skipped": "integer",
  "chunks_created": "integer",
  "chunks_updated": "integer",
  "chunks_deleted": "integer",
  "git_commit_sha": "string | null",
  "error_message": "string | null"
}
```

**Response:** `200 OK`

---

### POST /internal/analysis/{analysis_job_id}/agent-complete

**Purpose:** Called by the Celery agent task when an agent run completes or fails. Updates `agent_runs` record and checks if the parent job is fully complete.

**Auth:** Internal service key.

**Request Schema:**

```json
{
  "agent_run_id": "uuid",
  "status": "completed | failed",
  "findings_count": "integer",
  "rag_queries_count": "integer",
  "llm_tokens_used": "integer",
  "duration_ms": "integer",
  "error_message": "string | null"
}
```

**Response:** `200 OK`

---

### POST /internal/github/post-review

**Purpose:** Called by the PR review Celery task to trigger posting of review comments to GitHub after an analysis job completes.

**Auth:** Internal service key.

**Request Schema:**

```json
{
  "analysis_job_id": "uuid",
  "pr_review_id": "uuid"
}
```

**Response:** `200 OK`

---

## 31. API Lifecycle Flows

### 31.1 Repository Upload Lifecycle

This flow describes the complete API call sequence for uploading a ZIP archive and awaiting indexing completion.

```
1. Client → POST /repositories/upload
         ← 202 { repository_id, index_run_id, index_status: "pending" }

2. Server: Celery worker picks up indexing task
   - Validates archive, extracts to sandbox
   - Parses files, generates chunks and embeddings
   - Upserts vectors into Qdrant tenant collection
   - Updates PostgreSQL repository record: index_status → "indexing" → "ready"
   - Calls POST /internal/repositories/{id}/index-complete

3. Client → GET /repositories/{repository_id}
         ← 200 { index_status: "ready", total_chunks: 4821, last_indexed_at: "..." }
   (Client polls until index_status ∈ ["ready", "error"])

4. (Optional) Client → POST /repositories/{repository_id}/analysis
         ← 202 { analysis_job_id, status: "pending" }

5. Client → GET /analysis/{analysis_job_id}/stream   (SSE)
         ← event: agent_started (×8 agents)
         ← event: agent_completed (per agent as they finish)
         ← event: job_completed

6. Client → GET /repositories/{repository_id}/findings
         ← 200 { items: [...], pagination: {...} }
```

---

### 31.2 Repository Analysis Lifecycle

This flow describes triggering a full analysis and consuming the results.

```
1. Client → POST /repositories/{repository_id}/analysis
           Body: { analysis_type: "full", agents: [...all...] }
         ← 202 { analysis_job_id, status: "pending" }

2. Server: Analysis Orchestration Service creates analysis_job record
   - Dispatches Celery group: one task per agent
   - Each agent: RAG retrieval → LLM reasoning → structured findings output

3. Client → SSE: GET /analysis/{analysis_job_id}/stream
         ← event: agent_started for each agent
         ← event: agent_completed / agent_failed as agents finish
         ← event: job_completed { total_findings, composite_health_score }

4. Client → GET /analysis/{analysis_job_id}
         ← 200 { status: "completed", agent_runs: [...], composite_health_score: 74.5 }

5. Client → GET /repositories/{repository_id}/findings?severity=critical&status=open
         ← 200 { items: [...], pagination: {...} }

6. Client → PATCH /findings/{finding_id}/status
           Body: { status: "false_positive", comment: "..." }
         ← 200 (updated finding)

7. Client → GET /repositories/{repository_id}/agents/security/latest
         ← 200 { security_health_score, exposed_secrets_count, findings: [...] }
```

---

### 31.3 Chat Request Lifecycle

This flow describes the complete sequence for a multi-turn repository-aware chat interaction.

```
1. Client → POST /chat/sessions
           Body: { repository_ids: ["uuid"], scope: { type: "repository" } }
         ← 201 { session_id, repository_ids, scope }

2. Client → POST /chat/sessions/{session_id}/messages
           Body: { content: "How does authentication work in this codebase?" }
         ← SSE stream:
             event: token { token: "Authentication", sequence: 1 }
             event: token { token: " is handled...", sequence: 2 }
             ...
             event: citation { file_path: "src/auth/jwt.py", line_start: 12, line_end: 40 }
             event: complete { message_id: "uuid", rag_sources_count: 3 }

3. Client → POST /chat/sessions/{session_id}/messages
           Body: { content: "Show me the token expiry logic specifically",
                   scope_override: { type: "file", path: "src/auth/jwt.py" } }
         ← SSE stream (scoped to file)

4. Client → POST /chat/sessions/{session_id}/messages/{message_id}/feedback
           Body: { feedback_type: "positive" }
         ← 204

5. Client → GET /chat/sessions/{session_id}
         ← 200 { messages: [...all turns...], pagination }
```

---

### 31.4 Pull Request Review Lifecycle

This flow describes the automated PR review cycle triggered by a GitHub webhook.

```
1. GitHub → POST /webhooks/github
           Headers: X-GitHub-Event: pull_request, X-Hub-Signature-256: sha256=...
           Body: { action: "opened", pull_request: { number: 42, ... } }
         ← 200 { status: "accepted" }

2. Server: Webhook handler validates signature
   - Deduplicates via X-GitHub-Delivery in Redis
   - Enqueues Celery task: process_github_pr_webhook

3. Celery Worker:
   - Fetches PR diff via GitHub API
   - Creates analysis_job with analysis_type: "pr", scope: { type: "pr", pr_number: 42 }
   - Dispatches Code Review Agent + Bug Detection Agent + Security Agent concurrently

4. Server: Internal call → POST /internal/analysis/{id}/agent-complete (×3 agents)
   - Analysis Orchestration Service detects all agents complete
   - Triggers: POST /internal/github/post-review

5. GitHub PR Review Worker:
   - Formats findings as GitHub review comments
   - POSTs inline comments at correct file/line positions via GitHub API
   - Creates GitHub PR review (verdict: request_changes)
   - Creates GitHub Check Run (status: failure if critical findings present)
   - Updates github_pr_reviews record

6. (Human developer pushes fix) → GitHub push event on PR branch
         → GitHub → POST /webhooks/github (event: pull_request, action: synchronize)
         → Repeat from step 2 (incremental re-analysis on diff)

7. Client → GET /github/repositories/{repository_id}/pr-reviews?pr_number=42
         ← 200 { review_verdict: "request_changes", critical_findings: 1, posted_at: "..." }
```

---

*End of API Specification Document*

---

*This API specification is derived from PRD v1.0, Architecture v1.0, and Database Design v1.0. All route definitions, schema fields, and permission requirements must remain consistent with those source documents. Any new endpoints or schema changes must be reflected here before FastAPI router implementation begins.*
