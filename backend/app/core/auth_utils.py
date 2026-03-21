"""
NEXUS Platform — JWT Auth Utilities
=====================================
Provides password hashing, JWT creation/verification, and a FastAPI
dependency for extracting the current authenticated user.

Token strategy:
  - Access token  : 15-minute HS256 JWT (sent in Authorization header)
  - Refresh token : 32-byte random token stored in Redis with 7-day TTL
"""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS   = 7
ALGORITHM                    = "HS256"

_bearer = HTTPBearer(auto_error=False)


# ── Password hashing (bcrypt via passlib) ─────────────────────────────────────

def _get_pwd_context():
    from passlib.context import CryptContext
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _get_pwd_context().hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _get_pwd_context().verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _secret() -> str:
    from app.core.config import get_settings
    return get_settings().JWT_SECRET_KEY


def create_access_token(user_id: str, email: str, name: str) -> str:
    from jose import jwt as _jwt
    payload = {
        "sub":   user_id,
        "email": email,
        "name":  name,
        "exp":   datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat":   datetime.utcnow(),
        "type":  "access",
    }
    return _jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def create_refresh_token() -> str:
    """Generate a cryptographically random refresh token (not a JWT)."""
    return secrets.token_urlsafe(48)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token.
    Raises HTTPException 401 on any failure.
    """
    from jose import JWTError, ExpiredSignatureError
    from jose import jwt as _jwt
    try:
        payload = _jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token type")
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Access token expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid access token")


# ── Redis user store helpers ──────────────────────────────────────────────────

_redis_client = None

def _redis():
    """Return a Redis client, or None if Redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        from app.core.config import get_settings
        client = redis.from_url(get_settings().redis_url, decode_responses=True)
        client.ping()
        _redis_client = client
        return client
    except Exception:
        return None


def _user_key_by_email(email: str) -> str:
    return f"nexus:user:email:{email.lower()}"


def _user_key_by_id(user_id: str) -> str:
    return f"nexus:user:id:{user_id}"


def _refresh_key(token: str) -> str:
    return f"nexus:refresh:{token}"


# ── In-memory fallback (dev/demo when Redis is unavailable) ──────────────────

_mem_users_by_email: dict[str, dict] = {}
_mem_users_by_id:    dict[str, dict] = {}
_mem_refresh:        dict[str, str]  = {}


def create_admin_user() -> None:
    """
    Seed the default admin account if it doesn't already exist.
    Called once at application startup.
    """
    import uuid
    from datetime import datetime
    email = "admin@nexus.ai"
    if get_user_by_email(email):
        return  # already exists
    admin = {
        "id":                    str(uuid.uuid4()),
        "name":                  "NEXUS Admin",
        "email":                 email,
        "hashed_password":       hash_password("123password"),
        "role":                  "admin",
        "created_at":            datetime.utcnow().isoformat(),
        "force_password_change": True,
    }
    store_user(admin)
    logger.info("Default admin account created: admin@nexus.ai (password change required on first login)")


def store_user(user: dict) -> None:
    """Persist a user dict keyed by email and id."""
    import json
    r = _redis()
    if r:
        payload = json.dumps(user)
        r.set(_user_key_by_email(user["email"]), payload)
        r.set(_user_key_by_id(user["id"]), payload)
    else:
        _mem_users_by_email[user["email"].lower()] = user
        _mem_users_by_id[user["id"]] = user


def get_user_by_email(email: str) -> Optional[dict]:
    import json
    r = _redis()
    if r:
        raw = r.get(_user_key_by_email(email.lower()))
        return json.loads(raw) if raw else None
    return _mem_users_by_email.get(email.lower())


def get_user_by_id(user_id: str) -> Optional[dict]:
    import json
    r = _redis()
    if r:
        raw = r.get(_user_key_by_id(user_id))
        return json.loads(raw) if raw else None
    return _mem_users_by_id.get(user_id)


def store_refresh_token(token: str, user_id: str) -> None:
    r = _redis()
    ttl = REFRESH_TOKEN_EXPIRE_DAYS * 86400
    if r:
        r.setex(_refresh_key(token), ttl, user_id)
    else:
        _mem_refresh[token] = user_id


def get_refresh_token_owner(token: str) -> Optional[str]:
    r = _redis()
    if r:
        val = r.get(_refresh_key(token))
        return val.decode() if val else None
    return _mem_refresh.get(token)


def delete_refresh_token(token: str) -> None:
    r = _redis()
    if r:
        r.delete(_refresh_key(token))
    else:
        _mem_refresh.pop(token, None)


# ── FastAPI dependency: require authenticated user ────────────────────────────

async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency — extracts and validates the Bearer JWT.

    Usage:
        @router.get("/me")
        async def me(user = Depends(get_current_user)):
            ...
    """
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(creds.credentials)
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User no longer exists")
    return user
