"""
NEXUS Platform — Design Reviews Router
========================================
Team members submit approve / request_changes / reject decisions on completed
pipeline sessions. Each decision triggers a notification to the reviewer's
configured channels (Slack, Teams, email).

Endpoints:
  GET  /api/v1/reviews/{session_id}        — list all reviews for a session
  POST /api/v1/reviews/{session_id}        — submit / update your review
  GET  /api/v1/reviews/{session_id}/status — aggregated decision status
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth_utils import get_current_user, _redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])

ReviewAction = Literal["approve", "request_changes", "reject"]

# ── In-memory fallback ─────────────────────────────────────────────────────────

_mem: dict[str, list] = {}


def _key(session_id: str) -> str:
    return f"nexus:reviews:{session_id}"


def _load(session_id: str) -> list[dict]:
    r = _redis()
    if r:
        raw = r.get(_key(session_id))
        return json.loads(raw) if raw else []
    return list(_mem.get(session_id, []))


def _save(session_id: str, reviews: list[dict]) -> None:
    r = _redis()
    if r:
        r.set(_key(session_id), json.dumps(reviews))
    else:
        _mem[session_id] = reviews


# ── Schemas ────────────────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    action:  ReviewAction
    comment: str = ""


class ReviewOut(BaseModel):
    id:            str
    session_id:    str
    reviewer_id:   str
    reviewer_name: str
    action:        ReviewAction
    comment:       str
    created_at:    str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _decision(reviews: list[dict]) -> str:
    counts: dict[str, int] = {"approve": 0, "request_changes": 0, "reject": 0}
    for r in reviews:
        counts[r["action"]] = counts.get(r["action"], 0) + 1
    if not reviews:
        return "pending"
    if counts["approve"] > counts["reject"] and counts["approve"] > counts["request_changes"]:
        return "approved"
    if counts["reject"] > counts["approve"]:
        return "rejected"
    if counts["request_changes"] > 0:
        return "changes_requested"
    return "pending"


async def _load_session(session_id: str) -> dict:
    try:
        from app.memory.session_store import SessionStore
        from app.core.config import get_settings
        store = SessionStore(get_settings().redis_url)
        store.initialize()
        s = store.get(session_id)
        return s if s else {"id": session_id, "name": session_id}
    except Exception:
        return {"id": session_id, "name": session_id}


async def _notify(session_id: str, review: dict, reviewer: dict) -> None:
    """Fire-and-forget review notifications to reviewer's configured channels."""
    try:
        from app.core.notifiers import (
            build_slack_review, build_teams_review, build_email_review,
            send_slack, send_teams, send_email,
        )
        from app.routers.integrations import _load, APP_URL

        session = await _load_session(session_id)
        cfg     = _load(reviewer["id"])

        if cfg.get("slack_webhook"):
            await send_slack(cfg["slack_webhook"], build_slack_review(session, review, APP_URL))

        if cfg.get("teams_webhook"):
            await send_teams(cfg["teams_webhook"], build_teams_review(session, review, APP_URL))

        smtp       = cfg.get("smtp")
        recipients = cfg.get("email_recipients", [])
        if smtp and recipients:
            subject, html = build_email_review(session, review, APP_URL)
            await send_email(
                smtp_host=smtp["host"], smtp_port=smtp["port"],
                smtp_user=smtp["user"], smtp_password=smtp["password"],
                from_addr=smtp["from_addr"], to_addrs=recipients,
                subject=subject, html_body=html, use_tls=smtp.get("use_tls", True),
            )
    except Exception as e:
        logger.warning(f"Review notification failed: {e}")


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/{session_id}", response_model=list[ReviewOut])
async def list_reviews(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    return _load(session_id)


@router.post("/{session_id}", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def submit_review(
    session_id:   str,
    body:         ReviewRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit or update your review for a session. One review per user per session."""
    reviews = _load(session_id)

    # Find existing review by this user and update it
    idx = next((i for i, r in enumerate(reviews) if r["reviewer_id"] == current_user["id"]), None)

    review: dict = {
        "id":            reviews[idx]["id"] if idx is not None else str(uuid.uuid4()),
        "session_id":    session_id,
        "reviewer_id":   current_user["id"],
        "reviewer_name": current_user["name"],
        "action":        body.action,
        "comment":       body.comment,
        "created_at":    datetime.utcnow().isoformat(),
    }

    if idx is not None:
        reviews[idx] = review
    else:
        reviews.append(review)

    _save(session_id, reviews)
    logger.info(f"Review: session={session_id} user={current_user['email']} action={body.action}")

    # Notify asynchronously (don't block the response)
    import asyncio
    asyncio.create_task(_notify(session_id, review, current_user))

    return review


@router.get("/{session_id}/status")
async def review_status(
    session_id:   str,
    current_user: dict = Depends(get_current_user),
):
    """Aggregated decision status and vote counts for a session."""
    reviews = _load(session_id)
    counts  = {"approve": 0, "request_changes": 0, "reject": 0}
    for r in reviews:
        counts[r["action"]] = counts.get(r["action"], 0) + 1

    return {
        "session_id": session_id,
        "total":      len(reviews),
        "counts":     counts,
        "decision":   _decision(reviews),
        "reviews":    reviews,
    }


@router.delete("/{session_id}/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    session_id:   str,
    review_id:    str,
    current_user: dict = Depends(get_current_user),
):
    """Remove your own review."""
    reviews = _load(session_id)
    filtered = [r for r in reviews if not (r["id"] == review_id and r["reviewer_id"] == current_user["id"])]
    if len(filtered) == len(reviews):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found or not yours")
    _save(session_id, filtered)
