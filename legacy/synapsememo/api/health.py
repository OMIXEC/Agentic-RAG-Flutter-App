"""Health / readiness probe endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "synapsememo"}


@router.get("/ready")
async def readiness():
    return {"status": "ready"}
