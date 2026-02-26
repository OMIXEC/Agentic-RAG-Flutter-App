"""Supabase Auth JWT verification.

Replaces the old backend/auth.py manual JWT handling.  Works with both
Supabase-hosted and self-hosted (Supabase Auth / GoTrue) JWTs.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    import jwt as pyjwt
except ImportError:  # pragma: no cover
    pyjwt = None  # type: ignore[assignment]

from synapsememo.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class AuthUser:
    """Authenticated user extracted from a verified JWT."""

    user_id: str
    email: str | None = None
    role: str | None = None


def _decode_jwt(token: str, settings: Settings) -> dict:
    if pyjwt is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PyJWT is not installed on the backend.",
        )

    # Determine the secret — Supabase JWT secret takes priority
    secret = settings.supabase_jwt_secret or settings.supabase_anon_key
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No JWT secret configured (set SUPABASE_JWT_SECRET).",
        )

    try:
        decode_opts: dict = {
            "algorithms": [settings.jwt_algorithm],
            "options": {"verify_aud": False},  # Supabase tokens use 'authenticated'
        }
        if settings.jwt_audience:
            decode_opts["audience"] = settings.jwt_audience
            decode_opts["options"]["verify_aud"] = True
        if settings.jwt_issuer:
            decode_opts["issuer"] = settings.jwt_issuer

        payload: dict = pyjwt.decode(token, secret, **decode_opts)
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except pyjwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AuthUser:
    """FastAPI dependency — extracts the authenticated user from the Bearer token."""
    payload = _decode_jwt(credentials.credentials, settings)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing 'sub' claim",
        )

    return AuthUser(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role"),
    )
