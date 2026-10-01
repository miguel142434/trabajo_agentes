"""Router raíz de la API — agrupa todos los sub-routers bajo /api."""

from fastapi import APIRouter

from app.api.routes import health, llm

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router)
api_router.include_router(llm.router)
