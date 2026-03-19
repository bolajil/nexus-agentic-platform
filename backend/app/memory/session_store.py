"""
NEXUS Platform — Redis Session Store
Manages engineering session state with Redis persistence.
Falls back to in-memory dict store if Redis is unavailable.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class InMemorySessionStore:
    """Fallback in-memory session store (non-persistent)."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        logger.warning("Using in-memory session store — data will not persist across restarts")

    def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    def set(self, key: str, value: str, ex: int = 86400) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def keys(self, pattern: str = "*") -> list[str]:
        if pattern == "*":
            return list(self._store.keys())
        # Simple prefix matching
        prefix = pattern.replace("*", "")
        return [k for k in self._store.keys() if k.startswith(prefix)]

    def ping(self) -> bool:
        return True


class SessionStore:
    """
    Redis-backed session store for NEXUS engineering sessions.
    Stores serialized session JSON with configurable TTL.
    """

    SESSION_PREFIX = "nexus:session:"
    SESSION_TTL_SECONDS = 86400 * 7  # 7 days

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        self.redis_url = redis_url
        self._client = None
        self._initialized = False

    def initialize(self) -> bool:
        """Connect to Redis. Falls back to in-memory if unavailable."""
        try:
            import redis

            client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            client.ping()
            self._client = client
            self._initialized = True
            logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except ImportError:
            logger.warning("redis package not installed — using in-memory store")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}) — using in-memory store")

        self._client = InMemorySessionStore()
        self._initialized = True
        return True

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    def save_session(self, session_dict: dict[str, Any]) -> bool:
        """Persist a session dict to Redis."""
        self._ensure_initialized()
        try:
            session_id = session_dict["id"]
            key = f"{self.SESSION_PREFIX}{session_id}"
            serialized = json.dumps(session_dict, default=str)
            self._client.set(key, serialized, ex=self.SESSION_TTL_SECONDS)
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a session by ID."""
        self._ensure_initialized()
        try:
            key = f"{self.SESSION_PREFIX}{session_id}"
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        self._ensure_initialized()
        try:
            key = f"{self.SESSION_PREFIX}{session_id}"
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        """List all sessions, sorted by creation time (newest first)."""
        self._ensure_initialized()
        sessions = []
        try:
            pattern = f"{self.SESSION_PREFIX}*"
            keys = self._client.keys(pattern)
            for key in keys[:limit]:
                raw = self._client.get(key)
                if raw:
                    try:
                        session = json.loads(raw)
                        sessions.append(session)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")

        # Sort by created_at descending
        sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
        return sessions

    def update_session_status(self, session_id: str, status: str) -> bool:
        """Quick-update session status field."""
        self._ensure_initialized()
        session = self.get_session(session_id)
        if session is None:
            return False
        session["status"] = status
        session["updated_at"] = datetime.utcnow().isoformat()
        return self.save_session(session)

    def ping(self) -> bool:
        """Check store connectivity."""
        self._ensure_initialized()
        try:
            return bool(self._client.ping())
        except Exception:
            return False
