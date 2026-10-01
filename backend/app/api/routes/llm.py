"""Endpoint de prueba para el LLM (Fase 2 — se mantiene funcional)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.llm import LLMRequest, LLMResponse
from app.services.llm_service import LLMService, get_llm_service

router = APIRouter(tags=["LLM"])


@router.post("/test-llm", response_model=LLMResponse, summary="Prueba del modelo LLM")
async def test_llm(
    body: LLMRequest,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMResponse:
    """Envía un prompt a Qwen a través de Ollama y devuelve la respuesta.

    Los errores de Ollama (timeout, modelo no encontrado, servicio caído)
    son capturados por los exception handlers globales registrados en main.py.
    """
    return LLMResponse(response=await service.generate(body.prompt))
