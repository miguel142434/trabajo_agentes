"""Punto de entrada de la aplicación FastAPI."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar base de datos
    await init_db()
    yield
    # Shutdown
    pass


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
        lifespan=lifespan,
        description=(
            "API para agente inteligente basado en RAG con Ollama, "
            "Qwen, LangChain y LangGraph."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
        swagger_ui_init_oauth={
            "clientId": "rag-frontend",
            "appName": "RAG Agent",
            "usePkceWithAuthorizationCodeGrant": True,
        }
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
    # Incluir router de health check
    app.include_router(health_router)

    # ------------------------------------------------------------------
    # Exception handlers globales
    # ------------------------------------------------------------------
    register_exception_handlers(app)

    return app


app = create_app()

