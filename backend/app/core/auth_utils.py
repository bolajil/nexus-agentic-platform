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


# ── SQLite fallback (persists across restarts when Redis is unavailable) ─────

import sqlite3
import os

_db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "users.db")
_db_conn = None

def _get_db():
    """Get SQLite connection for user persistence."""
    global _db_conn
    if _db_conn is not None:
        return _db_conn
    try:
        os.makedirs(os.path.dirname(_db_path), exist_ok=True)
        conn = sqlite3.connect(_db_path, check_same_thread=False)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        conn.commit()
        _db_conn = conn
        logger.info(f"SQLite user store initialized: {_db_path}")
        return conn
    except Exception as e:
        logger.warning(f"SQLite init failed: {e}")
        return None

# In-memory fallback (only if SQLite also fails)
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
        return
    
    # SQLite fallback
    db = _get_db()
    if db:
        payload = json.dumps(user)
        db.execute(
            "INSERT OR REPLACE INTO users (id, email, data) VALUES (?, ?, ?)",
            (user["id"], user["email"].lower(), payload)
        )
        db.commit()
        return
    
    # In-memory fallback (last resort)
    _mem_users_by_email[user["email"].lower()] = user
    _mem_users_by_id[user["id"]] = user


def get_user_by_email(email: str) -> Optional[dict]:
    import json
    r = _redis()
    if r:
        raw = r.get(_user_key_by_email(email.lower()))
        return json.loads(raw) if raw else None
    
    # SQLite fallback
    db = _get_db()
    if db:
        cur = db.execute("SELECT data FROM users WHERE email = ?", (email.lower(),))
        row = cur.fetchone()
        return json.loads(row[0]) if row else None
    
    return _mem_users_by_email.get(email.lower())


def get_user_by_id(user_id: str) -> Optional[dict]:
    import json
    r = _redis()
    if r:
        raw = r.get(_user_key_by_id(user_id))
        return json.loads(raw) if raw else None
    
    # SQLite fallback
    db = _get_db()
    if db:
        cur = db.execute("SELECT data FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return json.loads(row[0]) if row else None
    
    return _mem_users_by_id.get(user_id)


def store_refresh_token(token: str, user_id: str) -> None:
    import time
    r = _redis()
    ttl = REFRESH_TOKEN_EXPIRE_DAYS * 86400
    if r:
        r.setex(_refresh_key(token), ttl, user_id)
        return
    
    # SQLite fallback
    db = _get_db()
    if db:
        expires_at = int(time.time()) + ttl
        db.execute(
            "INSERT OR REPLACE INTO refresh_tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at)
        )
        db.commit()
        return
    
    _mem_refresh[token] = user_id


def get_refresh_token_owner(token: str) -> Optional[str]:
    import time
    r = _redis()
    if r:
        val = r.get(_refresh_key(token))
        return val if val else None  # decode_responses=True means val is already str
    
    # SQLite fallback
    db = _get_db()
    if db:
        cur = db.execute(
            "SELECT user_id FROM refresh_tokens WHERE token = ? AND expires_at > ?",
            (token, int(time.time()))
        )
        row = cur.fetchone()
        return row[0] if row else None
    
    return _mem_refresh.get(token)


def delete_refresh_token(token: str) -> None:
    r = _redis()
    if r:
        r.delete(_refresh_key(token))
        return
    
    # SQLite fallback
    db = _get_db()
    if db:
        db.execute("DELETE FROM refresh_tokens WHERE token = ?", (token,))
        db.commit()
        return
    
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
