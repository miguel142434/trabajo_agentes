"""Punto de entrada de la aplicación FastAPI (Fase 3 — arquitectura profesional)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    """Factory que construye y configura la instancia de FastAPI."""
    settings = get_settings()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    setup_logging(settings.log_level)

    # ------------------------------------------------------------------
    # Aplicación
    # ------------------------------------------------------------------
    app = FastAPI(
        title=settings.app_title,
        description=(
            "API para agente inteligente basado en RAG con Ollama, "
            "Qwen, LangChain y LangGraph."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    app.include_router(api_router)
    # Mantener la ruta pública original y el alias /api/health de la fase 3.
    app.include_router(health_router)

    # ------------------------------------------------------------------
    # Exception handlers globales
    # ------------------------------------------------------------------
    register_exception_handlers(app)

    return app


app = create_app()
