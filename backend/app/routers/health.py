"""
NEXUS Platform — Health & Readiness Router
==========================================
Liveness and readiness probes for Docker/Kubernetes health checks.
"""
from __future__ import annotations

import time
from datetime import datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])

START_TIME = time.time()


@router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/ready")
async def readiness():
    """Readiness probe — checks all dependencies are available."""
    from app.core.config import get_settings
    settings = get_settings()

    checks = {
        "api": True,
        "openai_configured": bool(settings.openai_api_key),
        "uptime_seconds": round(time.time() - START_TIME, 1),
    }

    # Optional Redis check
    try:
        from app.memory.session_store import SessionStore
        store = SessionStore(settings.redis_url)
        checks["redis"] = store.ping()
    except Exception:
        checks["redis"] = False

    all_ready = checks["api"] and checks["openai_configured"]
    return {
        "status": "ready" if all_ready else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }
