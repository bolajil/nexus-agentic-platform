"""
NEXUS Platform — Integrations Router
======================================
Manages per-user Slack / Teams / Email notification configs and
dispatches share notifications when a pipeline result is ready for review.

Endpoints:
  GET  /api/v1/integrations            — fetch current user's config (SMTP password masked)
  POST /api/v1/integrations            — save config
  POST /api/v1/integrations/test/slack — send a test Slack message
  POST /api/v1/integrations/test/teams — send a test Teams message
  POST /api/v1/integrations/test/email — send a test email
  POST /api/v1/integrations/share      — share a session result to configured channels
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth_utils import get_current_user, _redis
from app.core.notifiers import (
    build_email_share,
    build_slack_share,
    build_teams_share,
    send_email,
    send_slack,
    send_teams,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

def _app_url() -> str:
    try:
        from app.core.config import get_settings
        return get_settings().NEXUS_APP_URL
    except Exception:
        return "http://localhost:3002"

APP_URL = _app_url()

_MASK = "••••••••"

# ── In-memory fallback ─────────────────────────────────────────────────────────

_mem: dict[str, dict] = {}


def _key(user_id: str) -> str:
    return f"nexus:integrations:{user_id}"


def _load(user_id: str) -> dict:
    r = _redis()
    if r:
        raw = r.get(_key(user_id))
        return json.loads(raw) if raw else {}
    return _mem.get(user_id, {})


def _save(user_id: str, cfg: dict) -> None:
    r = _redis()
    if r:
        r.set(_key(user_id), json.dumps(cfg))
    else:
        _mem[user_id] = cfg


# ── Schemas ────────────────────────────────────────────────────────────────────

class SmtpConfig(BaseModel):
    host:      str
    port:      int  = 465
    user:      str
    password:  str
    from_addr: str
    use_tls:   bool = True


class IntegrationsConfig(BaseModel):
    slack_webhook:    Optional[str]       = None
    teams_webhook:    Optional[str]       = None
    smtp:             Optional[SmtpConfig] = None
    email_recipients: list[str]           = []


class ShareRequest(BaseModel):
    session_id: str
    note:       str       = ""
    channels:   list[str]          # e.g. ["slack", "teams", "email"]
    email_to:   list[str] = []     # optional override for recipients


# ── Helpers ────────────────────────────────────────────────────────────────────

def _masked(cfg: dict) -> dict:
    """Return config with SMTP password replaced by mask for safe API responses."""
    import copy
    out = copy.deepcopy(cfg)
    if out.get("smtp") and out["smtp"].get("password"):
        out["smtp"]["password"] = _MASK
    return out


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


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("")
async def get_integrations(current_user: dict = Depends(get_current_user)):
    """Return the current user's integration config (SMTP password masked)."""
    return _masked(_load(current_user["id"]))


@router.post("", status_code=status.HTTP_200_OK)
async def save_integrations(
    body: IntegrationsConfig,
    current_user: dict = Depends(get_current_user),
):
    """Persist integration settings. Preserves existing SMTP password if masked placeholder is sent."""
    existing = _load(current_user["id"])
    cfg = body.model_dump(exclude_none=True)

    # Don't overwrite saved password with the UI mask
    if cfg.get("smtp") and cfg["smtp"].get("password") == _MASK:
        cfg["smtp"]["password"] = existing.get("smtp", {}).get("password", "")

    _save(current_user["id"], cfg)
    return {"message": "Integration settings saved"}


@router.post("/test/slack")
async def test_slack(current_user: dict = Depends(get_current_user)):
    cfg     = _load(current_user["id"])
    webhook = cfg.get("slack_webhook")
    if not webhook:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No Slack webhook configured")

    ok = await send_slack(webhook, {
        "text": f"⬡ NEXUS connection test from *{current_user['name']}* — Slack is working!",
    })
    if not ok:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Slack webhook returned an error")
    return {"message": "Test message sent to Slack"}


@router.post("/test/teams")
async def test_teams(current_user: dict = Depends(get_current_user)):
    cfg     = _load(current_user["id"])
    webhook = cfg.get("teams_webhook")
    if not webhook:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No Teams webhook configured")

    ok = await send_teams(webhook, {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [{
                    "type": "TextBlock",
                    "text": f"⬡ NEXUS connection test from {current_user['name']} — Teams is working!",
                    "weight": "Bolder",
                }],
            },
        }],
    })
    if not ok:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Teams webhook returned an error")
    return {"message": "Test message sent to Teams"}


@router.post("/test/email")
async def test_email(current_user: dict = Depends(get_current_user)):
    cfg        = _load(current_user["id"])
    smtp       = cfg.get("smtp")
    recipients = cfg.get("email_recipients", [])

    if not smtp:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No SMTP configuration saved")
    if not recipients:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No email recipients configured")

    ok = await send_email(
        smtp_host=smtp["host"],
        smtp_port=smtp["port"],
        smtp_user=smtp["user"],
        smtp_password=smtp["password"],
        from_addr=smtp["from_addr"],
        to_addrs=recipients,
        subject="[NEXUS] Email integration test",
        html_body=(
            "<p style='font-family:sans-serif'>"
            f"⬡ NEXUS email integration is working! "
            f"Sent by <strong>{current_user['name']}</strong>.</p>"
        ),
        use_tls=smtp.get("use_tls", True),
    )
    if not ok:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Email send failed — check SMTP settings")
    return {"message": f"Test email sent to {', '.join(recipients)}"}


@router.post("/share")
async def share_session(
    body: ShareRequest,
    current_user: dict = Depends(get_current_user),
):
    """Share a completed pipeline session to Slack, Teams, and/or email."""
    cfg     = _load(current_user["id"])
    session = await _load_session(body.session_id)
    results: dict[str, Optional[bool]] = {}

    if "slack" in body.channels:
        webhook = cfg.get("slack_webhook")
        if not webhook:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Slack not configured")
        results["slack"] = await send_slack(
            webhook,
            build_slack_share(session, body.note, current_user["name"], APP_URL),
        )

    if "teams" in body.channels:
        webhook = cfg.get("teams_webhook")
        if not webhook:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Teams not configured")
        results["teams"] = await send_teams(
            webhook,
            build_teams_share(session, body.note, current_user["name"], APP_URL),
        )

    if "email" in body.channels:
        smtp       = cfg.get("smtp")
        recipients = body.email_to or cfg.get("email_recipients", [])
        if not smtp:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email (SMTP) not configured")
        if not recipients:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No email recipients specified")
        subject, html = build_email_share(session, body.note, current_user["name"], APP_URL)
        results["email"] = await send_email(
            smtp_host=smtp["host"],
            smtp_port=smtp["port"],
            smtp_user=smtp["user"],
            smtp_password=smtp["password"],
            from_addr=smtp["from_addr"],
            to_addrs=recipients,
            subject=subject,
            html_body=html,
            use_tls=smtp.get("use_tls", True),
        )

    logger.info(f"Share dispatched by {current_user['email']}: {results}")
    return {"message": "Notifications dispatched", "results": results}
