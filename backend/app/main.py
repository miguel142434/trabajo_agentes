"""Punto de entrada de la aplicación FastAPI."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.database import init_db, engine
from app.services.document_service import get_document_service
from app.services.knowledge_base import KnowledgeBaseSeeder


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar base de datos
    await init_db()
    # Precargar la base de conocimiento global sin bloquear el arranque.
    seeding = None
    if get_settings().knowledge_base_seed_on_startup:
        seeder = KnowledgeBaseSeeder(get_settings(), get_document_service())
        seeding = asyncio.create_task(seeder.sync_with_retries())
    try:
        yield
    finally:
        if seeding is not None and not seeding.done():
            seeding.cancel()
            with suppress(asyncio.CancelledError):
                await seeding
        await engine.dispose()


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
            "clientId": settings.keycloak_client_id,
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

