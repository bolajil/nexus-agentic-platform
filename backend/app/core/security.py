"""
NEXUS Platform — Security Module
==================================
Implements defence-in-depth for the NEXUS API:

1. Security Headers     — HSTS, X-Frame-Options, CSP, referrer policy
2. Rate Limiting        — per-IP limits on the heavy pipeline endpoint (slowapi)
3. Optional API Key     — X-API-Key header; disabled in dev, enforced in prod
4. Input Sanitisation   — engineering brief length cap + content check

Design principle (for interviews):
  Auth is kept intentionally optional via REQUIRE_API_KEY setting so the
  demo works out-of-the-box without credentials.  In production you'd swap
  the API key check for a proper JWT/OAuth2 flow (e.g., Keycloak / Auth0).
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.responses import Response

logger = logging.getLogger(__name__)

# ── Security Headers ──────────────────────────────────────────────────────────

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "  # inline scripts needed for Next.js
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' https://cloud.langfuse.com; "
        "frame-ancestors 'none';"
    ),
}


async def add_security_headers(request: Request, call_next) -> Response:
    """Middleware: attach security headers to every response."""
    response: Response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


# ── Rate Limiting (slowapi) ───────────────────────────────────────────────────

def setup_rate_limiter(app):
    """
    Attach slowapi Limiter to the FastAPI app.

    Limits:
      POST /api/v1/sessions   → 5 requests / minute per IP
        (Each session triggers a full 6-agent LLM pipeline — expensive)
      All other endpoints      → 120 requests / minute per IP
        (Read ops are cheap — generous limit for dashboards/monitoring)

    In production, replace the in-memory key-func with a Redis backend:
        from slowapi.util import get_remote_address
        limiter = Limiter(key_func=get_remote_address, storage_uri="redis://...")
    """
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiter initialised (slowapi)")
        return limiter
    except ImportError:
        logger.warning("slowapi not installed — rate limiting disabled")
        return None


# ── Optional API Key Auth ─────────────────────────────────────────────────────

def _get_settings():
    """Lazy import to avoid circular deps."""
    from app.core.config import get_settings
    return get_settings()


async def verify_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> None:
    """
    FastAPI dependency: verify X-API-Key header when REQUIRE_API_KEY=true.

    Usage on a protected route:
        @router.post("/sessions", dependencies=[Depends(verify_api_key)])

    If NEXUS_API_KEY is not set in .env, the check is skipped.
    If REQUIRE_API_KEY=false (default), the check is skipped.
    This allows the demo to run without auth while shipping production-ready code.
    """
    settings = _get_settings()
    require_key = getattr(settings, 'REQUIRE_API_KEY', False)
    configured_key = getattr(settings, 'NEXUS_API_KEY', None)

    if not require_key or not configured_key:
        return  # Auth disabled — permit all

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Constant-time comparison to prevent timing attacks
    import hmac
    if not hmac.compare_digest(x_api_key.encode(), configured_key.encode()):
        logger.warning(f"Invalid API key attempt: key={x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )


# ── Input Sanitisation ────────────────────────────────────────────────────────

MAX_BRIEF_LENGTH = 4000   # characters
MIN_BRIEF_LENGTH = 20

# Simple prompt-injection guard: reject briefs that look like instruction overrides
_INJECTION_PATTERNS = re.compile(
    r"(ignore previous instructions|ignore all previous|"
    r"disregard.*system|you are now|act as if|pretend you are|"
    r"jailbreak|DAN mode)",
    re.IGNORECASE,
)


def sanitise_brief(brief: str) -> str:
    """
    Validate and sanitise an engineering brief before passing to the LLM pipeline.

    Raises HTTPException on:
      - Empty or too-short input
      - Input exceeding MAX_BRIEF_LENGTH
      - Detected prompt injection attempt

    Returns the sanitised brief (whitespace-normalised).
    """
    brief = brief.strip()

    if len(brief) < MIN_BRIEF_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Engineering brief too short (min {MIN_BRIEF_LENGTH} chars). "
                   "Please describe your design challenge in detail.",
        )

    if len(brief) > MAX_BRIEF_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Engineering brief too long (max {MAX_BRIEF_LENGTH} chars). "
                   "Please summarise your requirements.",
        )

    if _INJECTION_PATTERNS.search(brief):
        logger.warning(f"Prompt injection attempt detected: {brief[:100]!r}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid engineering brief content.",
        )

    # Normalise whitespace
    brief = re.sub(r"\s{3,}", " ", brief)
    return brief


# ── Static Analysis / Vulnerability Scanning (Bandit) ────────────────────────
# Run before production:
#   pip install bandit safety
#   bandit -r app/ -ll -ii          # Python security linter
#   safety check -r requirements.txt # Known CVE check on dependencies
#
# Integrate into CI (GitHub Actions example):
#   - name: Security scan
#     run: |
#       bandit -r backend/app -ll -ii --exit-zero
#       safety check -r backend/requirements.txt
