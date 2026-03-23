"""
NEXUS Platform — Human Feedback / Grader Router
================================================
Endpoints for collecting human feedback (thumbs up/down) on pipeline outputs.

Endpoints:
  POST   /feedback              — Submit feedback (thumbs up/down)
  GET    /feedback/stats        — Get aggregated feedback statistics
  GET    /feedback/{session_id} — Get all feedback for a session
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query

from app.core.config import get_settings
from app.models.schemas import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackScore,
    FeedbackStats,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])

# In-memory feedback store (production would use Redis/DB)
_feedback_store: dict[str, list[FeedbackResponse]] = defaultdict(list)


def _get_langfuse():
    """Get Langfuse client for score syncing."""
    settings = get_settings()
    pk = getattr(settings, 'LANGFUSE_PUBLIC_KEY', None)
    sk = getattr(settings, 'LANGFUSE_SECRET_KEY', None)
    
    if not (pk and sk):
        return None
    
    try:
        os.environ["LANGFUSE_PUBLIC_KEY"] = pk
        os.environ["LANGFUSE_SECRET_KEY"] = sk
        os.environ["LANGFUSE_HOST"] = getattr(settings, 'LANGFUSE_HOST', 'https://cloud.langfuse.com')
        
        from langfuse import Langfuse
        return Langfuse()
    except Exception as e:
        logger.warning(f"Failed to init Langfuse: {e}")
        return None


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackCreate) -> FeedbackResponse:
    """
    Submit human feedback on a session or specific agent output.
    
    - **session_id**: The session to rate
    - **score**: 1 = thumbs up, 0 = thumbs down
    - **agent_name**: Optional - rate a specific agent
    - **comment**: Optional text feedback
    - **user_id**: Optional user identifier
    """
    response = FeedbackResponse(
        session_id=feedback.session_id,
        score=feedback.score,
        agent_name=feedback.agent_name,
        comment=feedback.comment,
        user_id=feedback.user_id,
    )
    
    # Store feedback
    _feedback_store[feedback.session_id].append(response)
    
    # Sync to Langfuse if available
    lf = _get_langfuse()
    if lf:
        try:
            # Create score in Langfuse
            score_name = f"human_feedback_{feedback.agent_name}" if feedback.agent_name else "human_feedback"
            lf.score(
                trace_id=feedback.session_id,
                name=score_name,
                value=feedback.score.value,  # 0 or 1
                comment=feedback.comment,
                user_id=feedback.user_id,
            )
            lf.flush()
            logger.info(f"[{feedback.session_id}] Langfuse score synced: {score_name}={feedback.score.value}")
        except Exception as e:
            logger.warning(f"[{feedback.session_id}] Langfuse score sync failed: {e}")
    
    emoji = "👍" if feedback.score == FeedbackScore.THUMBS_UP else "👎"
    agent_info = f" (agent: {feedback.agent_name})" if feedback.agent_name else ""
    logger.info(f"[{feedback.session_id}] Feedback received: {emoji}{agent_info}")
    
    return response


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats() -> FeedbackStats:
    """Get aggregated feedback statistics across all sessions."""
    total = 0
    thumbs_up = 0
    thumbs_down = 0
    by_agent: dict[str, dict[str, int]] = defaultdict(lambda: {"thumbs_up": 0, "thumbs_down": 0})
    
    for session_id, feedbacks in _feedback_store.items():
        for fb in feedbacks:
            total += 1
            if fb.score == FeedbackScore.THUMBS_UP:
                thumbs_up += 1
                if fb.agent_name:
                    by_agent[fb.agent_name]["thumbs_up"] += 1
            else:
                thumbs_down += 1
                if fb.agent_name:
                    by_agent[fb.agent_name]["thumbs_down"] += 1
    
    approval_rate = thumbs_up / total if total > 0 else 0.0
    
    return FeedbackStats(
        total_feedback=total,
        thumbs_up=thumbs_up,
        thumbs_down=thumbs_down,
        approval_rate=round(approval_rate, 3),
        by_agent=dict(by_agent),
    )


@router.get("/{session_id}", response_model=list[FeedbackResponse])
async def get_session_feedback(session_id: str) -> list[FeedbackResponse]:
    """Get all feedback for a specific session."""
    feedbacks = _feedback_store.get(session_id, [])
    return feedbacks


@router.post("/thumbs-up/{session_id}", response_model=FeedbackResponse)
async def thumbs_up(
    session_id: str,
    agent_name: Optional[str] = Query(None, description="Specific agent to rate"),
    comment: Optional[str] = Query(None, description="Optional comment"),
    user_id: Optional[str] = Query(None, description="User ID"),
) -> FeedbackResponse:
    """Quick endpoint to submit a thumbs up for a session."""
    feedback = FeedbackCreate(
        session_id=session_id,
        score=FeedbackScore.THUMBS_UP,
        agent_name=agent_name,
        comment=comment,
        user_id=user_id,
    )
    return await submit_feedback(feedback)


@router.post("/thumbs-down/{session_id}", response_model=FeedbackResponse)
async def thumbs_down(
    session_id: str,
    agent_name: Optional[str] = Query(None, description="Specific agent to rate"),
    comment: Optional[str] = Query(None, description="Optional comment"),
    user_id: Optional[str] = Query(None, description="User ID"),
) -> FeedbackResponse:
    """Quick endpoint to submit a thumbs down for a session."""
    feedback = FeedbackCreate(
        session_id=session_id,
        score=FeedbackScore.THUMBS_DOWN,
        agent_name=agent_name,
        comment=comment,
        user_id=user_id,
    )
    return await submit_feedback(feedback)
