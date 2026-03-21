"""
NEXUS Platform — Auth Router
==============================
Endpoints:
  POST /api/auth/register   — create account, returns tokens
  POST /api/auth/login      — verify credentials, returns tokens
  POST /api/auth/refresh    — exchange refresh token for new access token
  POST /api/auth/logout     — invalidate refresh token
  GET  /api/auth/me         — return current user profile (protected)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator

from app.core.auth_utils import (
    create_access_token,
    create_refresh_token,
    delete_refresh_token,
    get_current_user,
    get_refresh_token_owner,
    get_user_by_email,
    get_user_by_id,
    hash_password,
    store_refresh_token,
    store_user,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request / Response schemas ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name:     str
    email:    EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          dict


class UserResponse(BaseModel):
    id:         str
    name:       str
    email:      str
    role:       str
    created_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _issue_tokens(user: dict) -> TokenResponse:
    access  = create_access_token(user["id"], user["email"], user["name"])
    refresh = create_refresh_token()
    store_refresh_token(refresh, user["id"])
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user={
            "id":    user["id"],
            "name":  user["name"],
            "email": user["email"],
            "role":  user["role"],
        },
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    """Create a new NEXUS account."""
    # Check duplicate email
    if get_user_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = {
        "id":              str(uuid.uuid4()),
        "name":            body.name.strip(),
        "email":           body.email.lower(),
        "hashed_password": hash_password(body.password),
        "role":            "user",
        "created_at":      datetime.utcnow().isoformat(),
    }
    store_user(user)
    logger.info(f"New user registered: {user['email']}")
    return _issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Authenticate and return JWT tokens."""
    user = get_user_by_email(body.email)

    # Use constant-time comparison path to avoid user-enumeration timing attacks
    dummy_hash = "$2b$12$dummyhashtopreventtimingattacks000000000000000000000000"
    hashed = user["hashed_password"] if user else dummy_hash

    if not verify_password(body.password, hashed) or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    logger.info(f"User logged in: {user['email']}")
    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    """Exchange a valid refresh token for a new access token."""
    user_id = get_refresh_token_owner(body.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    # Rotate refresh token (single-use)
    delete_refresh_token(body.refresh_token)
    return _issue_tokens(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest):
    """Invalidate the refresh token (access token expiry is handled client-side)."""
    delete_refresh_token(body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserResponse(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        role=current_user["role"],
        created_at=current_user["created_at"],
    )
