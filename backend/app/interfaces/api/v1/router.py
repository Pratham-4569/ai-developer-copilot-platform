"""API v1 route aggregator.

All v1 endpoint routers are registered here and mounted onto the FastAPI
application in ``app/main.py`` under the ``/api/v1`` prefix.

Phases add their routers here as they are implemented:
    Phase 2  → health (this file)
    Phase 4a → auth, tenants, users
    Phase 5  → repositories
    Phase 7  → rag
    Phase 8  → chat
    Phase 10 → analysis, agents, findings
    Phase 9  → github (webhook + integration)
    Phase 20 → dashboard
"""

from fastapi import APIRouter

from app.interfaces.api.v1.health import router as health_router

api_router = APIRouter()

# Phase 2 — Infrastructure Foundation
api_router.include_router(health_router)
