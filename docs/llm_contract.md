# LLM Implementation Contract

## Purpose

This contract defines how AI assistants must behave when generating architecture, code, documentation, tests, APIs, schemas, or implementation guidance for the AI-Powered Developer Copilot Platform.

The Constitution, PRD, Architecture, Database, API, and Roadmap documents are the source of truth.

---

## Mandatory Rules

1. Do not redesign the project.
2. Do not simplify the project.
3. Do not remove features.
4. Do not replace production-grade systems with simplified alternatives.
5. Do not remove the LangGraph multi-agent architecture.
6. Do not remove RAG capabilities.
7. Do not remove multi-tenancy.
8. Do not remove security requirements.
9. Do not remove observability requirements.
10. Do not remove audit logging requirements.
11. Do not convert the project into a CRUD application.
12. Do not introduce architectural drift from the source documents.

---

## Required Analysis Before Implementation

Before generating code, always verify:

### Vision Alignment

* What feature is being implemented?
* Why does it exist?
* How does it support the overall product vision?

### Architectural Alignment

* Which architecture layer owns this responsibility?
* Which services depend on it?
* Which future modules depend on it?

### Scalability Review

Consider:

* Horizontal scaling
* Async execution
* Caching
* Database load
* Queue load
* Failure recovery

### Security Review

Consider:

* Authentication
* Authorization
* Multi-tenancy
* Auditability
* Data isolation
* Input validation

---

## Required Response Structure

When generating implementation guidance, use the following structure.

### SECTION 1: Project Vision Verification

* Restate the current project vision.
* State which module is being built.
* Explain how the module integrates into the platform.
* Explain future dependencies.

### SECTION 2: Architecture Impact Analysis

Analyze:

* Scalability
* Performance
* Security
* Data Consistency
* Failure Modes

### SECTION 3: Implementation Plan

Provide:

* File locations
* Class structure
* Dependencies
* Build sequence

### SECTION 4: Production Grade Implementation

Provide:

* Robust code
* Strong typing
* Logging
* Error handling
* Validation
* Async-first design

No placeholders.

No TODO comments.

### SECTION 5: Future Integration Notes

Provide:

* Testing strategy
* Deployment considerations
* Monitoring considerations
* Edge cases
* Future integration points

---

## Code Quality Requirements

All generated code must:

* Be production-oriented
* Follow Clean Architecture
* Follow SOLID principles
* Follow strict typing
* Follow async-first design
* Include structured logging
* Include error handling
* Include validation
* Support observability

---

## Forbidden Behaviors

Do not:

* Generate demo code
* Generate toy examples
* Generate mock architectures
* Generate placeholder implementations
* Bypass service layers
* Access databases directly from controllers
* Place business logic in route handlers
* Ignore tenant boundaries
* Ignore RBAC
* Ignore audit logging

---

## Final Rule

If a request would reduce architecture quality, scalability, maintainability, security, or alignment with the Constitution, explain the issue and provide an alternative that remains consistent with the project architecture.
