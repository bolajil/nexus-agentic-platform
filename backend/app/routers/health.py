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


@router.get("/api/v1/langfuse/status")
async def langfuse_status():
    """Show live Langfuse config and send a test span. Open in browser to diagnose."""
    from app.core.config import get_settings
    settings = get_settings()

    pk = getattr(settings, 'LANGFUSE_PUBLIC_KEY', None)
    sk = getattr(settings, 'LANGFUSE_SECRET_KEY', None)
    host = getattr(settings, 'LANGFUSE_HOST', 'https://cloud.langfuse.com')

    result = {
        "public_key_set": bool(pk),
        "secret_key_set": bool(sk),
        "public_key_prefix": pk[:12] + "..." if pk else None,
        "host": host,
        "langfuse_module": None,
        "langchain_module": None,
        "auth_check": None,
        "span_sent": False,
        "error": None,
    }

    try:
        import langfuse as _lf
        import importlib.metadata
        result["langfuse_module"] = importlib.metadata.version("langfuse")
    except Exception as e:
        result["langfuse_module"] = f"ERROR: {e}"

    try:
        import langfuse.langchain
        result["langchain_module"] = "OK"
    except Exception as e:
        result["langchain_module"] = f"MISSING: {e}"

    if not (pk and sk):
        result["error"] = "Keys not set — add LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to backend/.env then restart uvicorn"
        return result

    try:
        from langfuse import Langfuse
        lf = Langfuse(public_key=pk, secret_key=sk, host=host)
        lf.auth_check()
        result["auth_check"] = "OK"

        span = lf.start_span(name="nexus-status-check",
                             metadata={"source": "status-endpoint"})
        span.update(output="status check OK")
        span.end()
        lf.flush()
        result["span_sent"] = True
    except Exception as e:
        result["error"] = str(e)

    return result


@router.get("/api/v1/langfuse/ping")
async def langfuse_ping():
    """
    Create a test trace in Langfuse to verify the connection end-to-end.
    Open http://localhost:8003/api/v1/langfuse/ping in the browser.
    If you see {"status": "ok"} the trace will appear in Langfuse within seconds.
    """
    from app.core.config import get_settings
    settings = get_settings()

    pk = getattr(settings, 'LANGFUSE_PUBLIC_KEY', None)
    sk = getattr(settings, 'LANGFUSE_SECRET_KEY', None)

    if not (pk and sk):
        return {"status": "not_configured", "detail": "LANGFUSE_PUBLIC_KEY / SECRET_KEY not set in .env"}

    try:
        from langfuse import Langfuse  # type: ignore
        lf = Langfuse(
            public_key=pk,
            secret_key=sk,
            host=getattr(settings, 'LANGFUSE_HOST', 'https://cloud.langfuse.com'),
        )
        trace = lf.trace(
            name="nexus-ping",
            session_id="ping-test",
            user_id="system",
            tags=["nexus", "ping"],
            metadata={"source": "health-endpoint"},
        )
        # Add a test span so it's clearly visible in Langfuse
        span = trace.span(name="connection-test", metadata={"msg": "NEXUS → Langfuse OK"})
        span.end()
        lf.flush()
        return {
            "status": "ok",
            "trace_id": trace.id,
            "message": "Trace sent — check Langfuse dashboard Tracing section now",
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}

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
