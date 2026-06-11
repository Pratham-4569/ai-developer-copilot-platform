# AI-Powered Developer Copilot Platform

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
