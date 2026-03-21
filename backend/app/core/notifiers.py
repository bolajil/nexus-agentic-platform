"""
NEXUS Platform — Notification Helpers
======================================
Sends formatted messages to Slack (Block Kit), Microsoft Teams (Adaptive Cards),
and email (SMTP). All async — uses httpx for webhooks, asyncio executor for SMTP.
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


# ── Low-level senders ─────────────────────────────────────────────────────────

async def send_slack(webhook_url: str, payload: dict) -> bool:
    """POST a Block Kit payload to a Slack incoming webhook."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        logger.warning(f"Slack notification failed: {e}")
        return False


async def send_teams(webhook_url: str, payload: dict) -> bool:
    """POST an Adaptive Card payload to a Teams incoming webhook."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            return resp.status_code in (200, 202)
    except Exception as e:
        logger.warning(f"Teams notification failed: {e}")
        return False


def _send_email_sync(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_addr: str,
    to_addrs: list[str],
    subject: str,
    html_body: str,
    use_tls: bool = True,
) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = ", ".join(to_addrs)
        msg.attach(MIMEText(html_body, "html"))

        if use_tls:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(from_addr, to_addrs, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(from_addr, to_addrs, msg.as_string())
        return True
    except Exception as e:
        logger.warning(f"Email notification failed: {e}")
        return False


async def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_addr: str,
    to_addrs: list[str],
    subject: str,
    html_body: str,
    use_tls: bool = True,
) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _send_email_sync(
            smtp_host, smtp_port, smtp_user, smtp_password,
            from_addr, to_addrs, subject, html_body, use_tls,
        ),
    )


# ── Slack message builders ─────────────────────────────────────────────────────

def build_slack_share(
    session: dict, note: str, sharer_name: str, app_url: str
) -> dict:
    """Block Kit payload for sharing a completed pipeline result."""
    domain       = session.get("domain") or (session.get("requirements") or {}).get("domain", "Engineering")
    session_name = session.get("name") or session.get("id", "Unknown")
    session_url  = f"{app_url}/sessions/{session.get('id', '')}"

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "⬡ NEXUS — Design Ready for Review", "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{session_name}*\n{sharer_name} shared a completed *{domain}* design for team review.",
            },
        },
    ]

    if note:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Note:* {note}"},
        })

    blocks += [
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [{
                "type": "button",
                "text": {"type": "plain_text", "text": "Review in NEXUS →", "emoji": True},
                "style": "primary",
                "url": session_url,
            }],
        },
    ]
    return {"blocks": blocks}


def build_slack_review(session: dict, review: dict, app_url: str) -> dict:
    """Block Kit payload when a review decision is submitted."""
    emoji  = {"approve": "✅", "request_changes": "🔄", "reject": "❌"}
    label  = {"approve": "Approved", "request_changes": "Changes Requested", "reject": "Rejected"}
    action = review.get("action", "")
    session_name = session.get("name") or session.get("id", "Unknown")
    session_url  = f"{app_url}/sessions/{session.get('id', '')}"

    text = (
        f"{emoji.get(action, '📋')} *Review on {session_name}*\n"
        f"*{review.get('reviewer_name', 'Someone')}* — {label.get(action, action)}"
    )
    if review.get("comment"):
        text += f"\n> {review['comment']}"

    return {
        "blocks": [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "View →"},
                "url": session_url,
            },
        }],
    }


# ── Teams message builders ─────────────────────────────────────────────────────

def build_teams_share(
    session: dict, note: str, sharer_name: str, app_url: str
) -> dict:
    """Adaptive Card payload for Teams incoming webhook."""
    domain       = session.get("domain") or (session.get("requirements") or {}).get("domain", "Engineering")
    session_name = session.get("name") or session.get("id", "Unknown")
    session_url  = f"{app_url}/sessions/{session.get('id', '')}"

    facts = [
        {"title": "Domain",    "value": domain},
        {"title": "Shared by", "value": sharer_name},
    ]
    if note:
        facts.append({"title": "Note", "value": note})

    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "⬡ NEXUS — Design Ready for Review",
                        "weight": "Bolder",
                        "size": "Medium",
                        "color": "Accent",
                    },
                    {"type": "TextBlock", "text": session_name, "weight": "Bolder", "wrap": True},
                    {"type": "FactSet", "facts": facts},
                ],
                "actions": [{
                    "type": "Action.OpenUrl",
                    "title": "Review in NEXUS →",
                    "url": session_url,
                }],
            },
        }],
    }


def build_teams_review(session: dict, review: dict, app_url: str) -> dict:
    """Adaptive Card payload for a review decision notification."""
    label  = {"approve": "Approved ✅", "request_changes": "Changes Requested 🔄", "reject": "Rejected ❌"}
    action = review.get("action", "")
    session_name = session.get("name") or session.get("id", "Unknown")
    session_url  = f"{app_url}/sessions/{session.get('id', '')}"

    facts = [
        {"title": "Session",  "value": session_name},
        {"title": "Reviewer", "value": review.get("reviewer_name", "Unknown")},
        {"title": "Decision", "value": label.get(action, action)},
    ]
    if review.get("comment"):
        facts.append({"title": "Comment", "value": review["comment"]})

    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": f"NEXUS Design Review — {label.get(action, action)}",
                        "weight": "Bolder",
                        "size": "Medium",
                    },
                    {"type": "FactSet", "facts": facts},
                ],
                "actions": [{
                    "type": "Action.OpenUrl",
                    "title": "View Full Report →",
                    "url": session_url,
                }],
            },
        }],
    }


# ── Email message builders ─────────────────────────────────────────────────────

_EMAIL_BASE = """
<html>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             max-width:600px;margin:0 auto;padding:24px;background:#f1f5f9">
  <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);
              padding:24px 28px;border-radius:12px 12px 0 0;color:white">
    <div style="font-size:20px;font-weight:700">⬡ NEXUS</div>
    <div style="font-size:14px;opacity:.8;margin-top:4px">{subtitle}</div>
  </div>
  <div style="background:white;padding:28px;border:1px solid #e2e8f0;
              border-top:none;border-radius:0 0 12px 12px">
    {body}
    <a href="{url}" style="display:inline-block;margin-top:20px;
       padding:12px 24px;background:#4f46e5;color:white;
       text-decoration:none;border-radius:8px;font-weight:600;font-size:14px">
      {cta}
    </a>
  </div>
  <p style="color:#94a3b8;font-size:11px;text-align:center;margin-top:16px">
    NEXUS Agentic Engineering Platform
  </p>
</body>
</html>
"""


def build_email_share(
    session: dict, note: str, sharer_name: str, app_url: str
) -> tuple[str, str]:
    """Return (subject, html_body) for a share notification email."""
    domain       = session.get("domain") or (session.get("requirements") or {}).get("domain", "Engineering")
    session_name = session.get("name") or session.get("id", "Unknown")
    session_url  = f"{app_url}/sessions/{session.get('id', '')}"
    note_html    = f"<p style='color:#475569'><strong>Note:</strong> {note}</p>" if note else ""

    body = f"""
      <h2 style="margin:0 0 8px;color:#0f172a">{session_name}</h2>
      <p style="color:#64748b;margin:0 0 12px">
        <strong>{sharer_name}</strong> shared a completed
        <strong>{domain}</strong> design for team review.
      </p>
      {note_html}
    """
    html = _EMAIL_BASE.format(
        subtitle="Design Ready for Review",
        body=body,
        url=session_url,
        cta="Review in NEXUS →",
    )
    subject = f"[NEXUS] {session_name} — Design Ready for Review"
    return subject, html


def build_email_review(
    session: dict, review: dict, app_url: str
) -> tuple[str, str]:
    """Return (subject, html_body) for a review decision email."""
    label  = {"approve": "Approved ✅", "request_changes": "Changes Requested 🔄", "reject": "Rejected ❌"}
    action = review.get("action", "")
    session_name  = session.get("name") or session.get("id", "Unknown")
    session_url   = f"{app_url}/sessions/{session.get('id', '')}"
    comment_html  = (
        f"<blockquote style='border-left:3px solid #e2e8f0;"
        f"padding-left:12px;color:#64748b;margin:12px 0'>"
        f"{review['comment']}</blockquote>"
        if review.get("comment") else ""
    )

    body = f"""
      <p style="color:#0f172a;font-size:16px;font-weight:600;margin:0 0 8px">
        {label.get(action, action)}
      </p>
      <p style="color:#64748b;margin:0 0 4px">
        <strong>{review.get('reviewer_name', 'A team member')}</strong>
        submitted a review on <strong>{session_name}</strong>.
      </p>
      {comment_html}
    """
    html = _EMAIL_BASE.format(
        subtitle=f"Review Decision — {label.get(action, action)}",
        body=body,
        url=session_url,
        cta="View Full Report →",
    )
    subject = f"[NEXUS Review] {label.get(action, action)} — {session_name}"
    return subject, html
