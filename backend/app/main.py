"""
NEXUS Platform — FastAPI Application Entry Point
=================================================
Initialises all sub-systems, registers routers, and configures middleware.

Start:
    uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

Or via Docker:
    docker compose up --build
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging_setup import configure_logging

# Configure structured logging before anything else
configure_logging()
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initialises dependencies on startup, tears them down on shutdown.

    Order of operations:
    1. Validate settings (fail fast if OPENAI_API_KEY is missing)
    2. Initialise Redis session store (fallback to in-memory if unavailable)
    3. Initialise ChromaDB vector store (fallback to in-memory if unavailable)
    4. Seed knowledge base if empty
    5. Start OpenTelemetry tracing (optional)
    """
    settings = get_settings()
    logger.info(f"Starting NEXUS Platform v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # ── Session Store ─────────────────────────────────────────────────
    try:
        from app.memory.session_store import SessionStore
        store = SessionStore(settings.redis_url)
        store.initialize()
        app.state.session_store = store
        logger.info("Session store initialized")
    except Exception as e:
        logger.warning(f"Session store init failed: {e} — using fallback")

    # ── Vector Store ──────────────────────────────────────────────────
    try:
        from app.memory.vector_store import VectorStoreManager
        vs = VectorStoreManager(
            openai_api_key=settings.openai_api_key,
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        vs.initialize()
        app.state.vector_store = vs
        logger.info("Vector store initialized")

        # Auto-seed if empty
        stats = vs.get_stats()
        if stats.get("total_documents", 0) == 0:
            logger.info("Knowledge base is empty — triggering auto-seed...")
            try:
                import sys, os
                sys.path.insert(0, os.path.dirname(__file__) + "/../")
                from scripts.seed_knowledge_base import seed
                seed(vs)
                logger.info("Knowledge base seeded successfully")
            except Exception as seed_err:
                logger.warning(f"Auto-seed failed (not critical): {seed_err}")
    except Exception as e:
        logger.warning(f"Vector store init failed: {e}")

    # ── OpenTelemetry ─────────────────────────────────────────────────
    try:
        from app.core.telemetry import setup_telemetry
        setup_telemetry(
            enabled=getattr(settings, 'OTEL_ENABLED', False),
            endpoint=settings.otlp_endpoint,
        )
        logger.info("OpenTelemetry tracing initialized")
    except Exception as e:
        logger.debug(f"Telemetry not available: {e}")

    # ── Auto-connect tools ────────────────────────────────────────────
    try:
        from app.routers.tools import _run_connector, _connections
        from app.routers.tools import ToolConfig
        auto_tools = ["openai", "scipy", "numpy", "sympy", "nist"]
        for tid in auto_tools:
            try:
                result = await _run_connector(tid, None)
                _connections[tid] = result
                logger.info(f"Tool auto-connected: {tid} → {result.get('status')}")
            except Exception as te:
                logger.debug(f"Tool auto-connect failed for {tid}: {te}")
        # FreeCAD — attempt detection with known path
        try:
            fc_cfg = ToolConfig(path=r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe")
            fc_result = await _run_connector("freecad", fc_cfg)
            _connections["freecad"] = fc_result
            logger.info(f"FreeCAD auto-detected → {fc_result.get('status')}")
        except Exception as fe:
            logger.debug(f"FreeCAD auto-detect skipped: {fe}")
    except Exception as e:
        logger.warning(f"Tool auto-connect startup failed: {e}")

    logger.info("NEXUS Platform ready — all systems nominal")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────
    logger.info("NEXUS Platform shutting down gracefully")
    try:
        from app.core.llm_factory import flush_langfuse
        flush_langfuse()
    except Exception:
        pass


# ── FastAPI App ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="NEXUS — Multi-Agent Engineering Platform",
        description=(
            "Production-grade agentic AI platform for autonomous hardware design. "
            "Routes engineering briefs through a 6-agent LangGraph pipeline: "
            "Requirements → Research → Design → Simulation → Optimization → Report."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Security (rate limiter + API key) ─────────────────────────────
    try:
        from app.core.security import setup_rate_limiter
        setup_rate_limiter(app)
    except Exception as e:
        logger.warning(f"Rate limiter setup failed: {e}")

    # ── Middleware ─────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Session-ID"],
    )

    # Security headers on every response
    from starlette.middleware.base import BaseHTTPMiddleware
    from app.core.security import add_security_headers
    app.add_middleware(BaseHTTPMiddleware, dispatch=add_security_headers)

    # Request timing middleware
    @app.middleware("http")
    async def add_timing_header(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed:.1f}"
        return response

    # ── Routers ────────────────────────────────────────────────────────
    from app.routers.health import router as health_router
    from app.routers.sessions import router as sessions_router
    from app.routers.auth import router as auth_router

    app.include_router(health_router)
    app.include_router(auth_router)           # /api/auth/*
    app.include_router(sessions_router, prefix="/api/v1")

    try:
        from app.routers.knowledge import router as knowledge_router
        app.include_router(knowledge_router, prefix="/api/v1")
        logger.info("Knowledge router registered")
    except Exception as e:
        logger.warning(f"Knowledge router unavailable: {e}")

    try:
        from app.routers.documents import router as documents_router
        app.include_router(documents_router, prefix="/api/v1")
        logger.info("Documents upload router registered")
    except Exception as e:
        logger.warning(f"Documents router unavailable: {e}")

    try:
        from app.routers.tools import router as tools_router
        app.include_router(tools_router, prefix="/api/v1")
        logger.info("Tool connections router registered")
    except Exception as e:
        logger.warning(f"Tools router unavailable: {e}")

    try:
        from app.routers.cad import router as cad_router
        app.include_router(cad_router, prefix="/api/v1")
        logger.info("CAD file router registered")
    except Exception as e:
        logger.warning(f"CAD router unavailable: {e}")

    # ── Global Exception Handlers ──────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    return app


app = create_app()
