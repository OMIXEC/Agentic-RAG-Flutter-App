"""SynapseMemo — FastAPI application factory.

This is the single entrypoint for the backend:
    uvicorn synapsememo.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from synapsememo.config import get_settings
from synapsememo.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description="SynapseMemo — Multimodal RAG Life Memory API",
        lifespan=lifespan,
    )

    # ── CORS ────────────────────────────────────────────────────────────
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────────────────
    from synapsememo.api.health import router as health_router
    from synapsememo.api.memories import router as memories_router

    application.include_router(health_router)
    application.include_router(memories_router)

    return application


# Module-level app for `uvicorn synapsememo.main:app`
app = create_app()
