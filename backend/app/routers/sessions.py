"""
NEXUS Platform — Sessions Router
=================================
REST + SSE endpoints for engineering session management.

Endpoints:
  POST   /sessions              — Create session and start pipeline (SSE stream)
  GET    /sessions              — List all sessions
  GET    /sessions/{id}         — Get single session detail
  DELETE /sessions/{id}         — Delete session
  GET    /sessions/{id}/stream  — Re-attach to a running session's SSE stream

SSE Streaming Pattern:
  The POST /sessions endpoint returns an EventStream immediately.
  The pipeline runs concurrently via asyncio.create_task().
  Events are pushed through an SSEQueue: agent_start → agent_thought →
  tool_call → tool_result → agent_complete → session_complete
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.agents.orchestrator import AgentState, NEXUSOrchestrator, SSEQueue
from app.memory.session_store import SessionStore
from app.models.schemas import (
    Session,
    SessionCreate,
    SessionStatus,
    SessionSummary,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["sessions"])

# Module-level singletons (initialized once at app startup)
_session_store: Optional[SessionStore] = None
_orchestrator: Optional[NEXUSOrchestrator] = None


def get_session_store() -> SessionStore:
    global _session_store
    if _session_store is None:
        settings = get_settings()
        _session_store = SessionStore(settings.redis_url)
        _session_store.initialize()
    return _session_store


def get_orchestrator(settings: Settings = Depends(get_settings)) -> NEXUSOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = NEXUSOrchestrator(settings, get_session_store())
    return _orchestrator


# ── SSE Helper ────────────────────────────────────────────────────────────────

async def _sse_generator(sse_queue: SSEQueue) -> AsyncIterator[str]:
    """
    Consume the SSEQueue and yield formatted SSE frames.

    Format per SSE spec:
        data: <json>\n\n

    Heartbeat events are sent every 15s to keep the connection alive
    through load balancers that aggressively close idle connections.
    """
    heartbeat_interval = 15.0
    last_heartbeat = asyncio.get_event_loop().time()

    async for event in sse_queue:
        yield f"data: {json.dumps(event, default=str)}\n\n"

        # Check if we should send a heartbeat
        now = asyncio.get_event_loop().time()
        if now - last_heartbeat > heartbeat_interval:
            heartbeat = {
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat(),
            }
            yield f"data: {json.dumps(heartbeat)}\n\n"
            last_heartbeat = now


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", status_code=200)
async def create_session(
    request: Request,
    body: SessionCreate,
    settings: Settings = Depends(get_settings),
    store: SessionStore = Depends(get_session_store),
    orchestrator: NEXUSOrchestrator = Depends(get_orchestrator),
) -> StreamingResponse:
    """
    Create a new engineering session and stream the pipeline execution.

    Returns an SSE stream. Each event has shape:
      { "type": "agent_start"|"agent_complete"|"tool_call"|..., "agent": str, "content": any }

    The client should listen until it receives a "session_complete" event.
    Session state is persisted to Redis at each agent boundary.
    """
    # Input sanitisation (prompt injection guard + length limits)
    from app.core.security import sanitise_brief
    body.engineering_brief = sanitise_brief(body.engineering_brief)

    session_id = str(uuid.uuid4())
    session_name = body.session_name or f"Session {session_id[:8]}"

    # Stable user ID from the frontend (persisted in localStorage)
    user_id = request.headers.get("X-User-ID") or session_id

    # Langfuse: track session creation event
    try:
        from app.core.llm_factory import get_langfuse_client
        _lf = get_langfuse_client(settings)
        if _lf:
            ev = _lf.start_span(
                name="session:created",
                metadata={
                    "session_id": session_id,
                    "session_name": session_name,
                    "user_id": user_id,
                    "brief_length": len(body.engineering_brief),
                    "brief_preview": body.engineering_brief[:150],
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )
            ev.end()
    except Exception:
        pass

    # Create initial session record
    initial_session = {
        "id": session_id,
        "name": session_name,
        "engineering_brief": body.engineering_brief,
        "status": "running",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "provenance_chain": [],
    }
    store.save_session(initial_session)

    # Build initial agent state
    initial_state: AgentState = {
        "session_id": session_id,
        "engineering_brief": body.engineering_brief,
        "provenance_chain": [],
        "messages": [],
        "is_complete": False,
    }

    # Create SSE queue and launch pipeline as background task
    sse_queue = SSEQueue()
    asyncio.create_task(orchestrator.run(initial_state, sse_queue, user_id=user_id))

    logger.info(f"[{session_id}] Pipeline started for brief: {body.engineering_brief[:80]}...")

    return StreamingResponse(
        _sse_generator(sse_queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",       # Disable nginx buffering
            "X-Session-ID": session_id,
        },
    )


@router.get("")
async def list_sessions(
    store: SessionStore = Depends(get_session_store),
) -> list[SessionSummary]:
    """Return summary of all sessions, newest first."""
    sessions = store.list_sessions(limit=100)
    summaries = []
    for s in sessions:
        brief = s.get("engineering_brief", "")
        req = s.get("requirements") or {}
        summaries.append(SessionSummary(
            id=s["id"],
            name=s.get("name", f"Session {s['id'][:8]}"),
            status=s.get("status", "pending"),
            created_at=s.get("created_at", datetime.utcnow().isoformat()),
            domain=req.get("domain"),
            brief_excerpt=brief[:120] + ("..." if len(brief) > 120 else ""),
        ))
    return summaries


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> dict:
    """Return full session state including all agent outputs and provenance chain."""
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> Response:
    """Delete a session from the store."""
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    store.delete_session(session_id)
    return Response(status_code=204)


@router.get("/{session_id}/provenance")
async def get_provenance(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> list[dict]:
    """
    Return the full provenance chain for a session.
    Each entry records: which agent ran, what tools it used,
    how long it took, confidence score, and input/output summaries.
    This is the explainability / audit trail endpoint.
    """
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session.get("provenance_chain", [])
