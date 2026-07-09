"""FastAPI bootstrap for Mentor."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.lib.logger import get_logger

logger = get_logger()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Mentor", version="0.1.0", description="An adaptive learning agent")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        """Liveness + active LLM provider. O(1)."""
        return {"status": "ok", "provider": settings.llm_provider}

    # API routers (registered in Phase 8).
    from app.api import paths, progress, reviews, sessions

    app.include_router(sessions.router)
    app.include_router(paths.router)
    app.include_router(reviews.router)
    app.include_router(progress.router)

    logger.info("Mentor started (provider=%s)", settings.llm_provider)
    return app


app = create_app()
