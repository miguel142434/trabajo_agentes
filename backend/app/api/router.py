"""Router raíz de la API — agrupa todos los sub-routers bajo /api."""

from fastapi import APIRouter, Depends

from app.api.routes import health, llm, vector, documents, chat, conversations
from app.core.security import get_current_user

api_router = APIRouter(prefix="/api")

# Rutas públicas
api_router.include_router(health.router)
api_router.include_router(llm.router, dependencies=[Depends(get_current_user)])

# Rutas protegidas
api_router.include_router(vector.router, dependencies=[Depends(get_current_user)])
api_router.include_router(documents.router, dependencies=[Depends(get_current_user)])
api_router.include_router(chat.router, dependencies=[Depends(get_current_user)])
api_router.include_router(conversations.router, dependencies=[Depends(get_current_user)])

