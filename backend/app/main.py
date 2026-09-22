from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.llm import router as llm_router

app = FastAPI(
    title="RAG Agent API",
    description="API para agente inteligente basado en RAG con Ollama, Qwen, LangChain y LangGraph",
    version="0.1.0",
)

app.include_router(llm_router)

# CORS — preparado para el frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Endpoint de salud para verificar que el backend está activo."""
    return {"status": "ok"}
