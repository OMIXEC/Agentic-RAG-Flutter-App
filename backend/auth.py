"""Supabase Auth JWT verification for the Unified Backend.

Extracted and adapted from legacy SynapseMemo auth system.
"""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None

from .config import settings

bearer_scheme = HTTPBearer(auto_error=True)

@dataclass(frozen=True)
class AuthUser:
    """Authenticated user extracted from verified Supabase JWT."""
    user_id: str
    email: str | None = None
    role: str | None = None

def _decode_supabase_jwt(token: str) -> dict:
    if pyjwt is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PyJWT is not installed on the backend environment.",
        )

    # Use SUPABASE_JWT_SECRET for symmetric validation (standard for Supabase)
    secret = settings.supabase_jwt_secret or settings.jwt_secret
    
    if not secret or secret == "dev-secret-change-me":
        # Check if ANON_KEY is provided as a fallback (some self-hosted setups use it)
        secret = settings.supabase_anon_key or secret

    try:
        # Supabase tokens usually have 'authenticated' in audience, 
        # but we can be flexible if audience is configured.
        decode_opts: dict = {
            "algorithms": [settings.jwt_algorithm],
            "options": {"verify_aud": False},
        }
        
        if settings.jwt_audience and settings.jwt_audience != "search-memory":
            decode_opts["audience"] = settings.jwt_audience
            decode_opts["options"]["verify_aud"] = True
            
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
) -> AuthUser:
    """FastAPI dependency to protect routes with Supabase Auth."""
    payload = _decode_supabase_jwt(credentials.credentials)
    
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
