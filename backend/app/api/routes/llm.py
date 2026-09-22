"""Endpoint temporal para comprobar la conexión con el LLM."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.llm import LLMRequest, LLMResponse
from app.services.llm_service import (
    LLMError,
    LLMModelNotFoundError,
    LLMService,
    LLMTimeoutError,
    LLMUnavailableError,
    get_llm_service,
)

router = APIRouter(prefix="/api", tags=["LLM"])


@router.post("/test-llm", response_model=LLMResponse)
async def test_llm(
    body: LLMRequest,
    service: Annotated[LLMService, Depends(get_llm_service)],
) -> LLMResponse:
    try:
        return LLMResponse(response=await service.generate(body.prompt))
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except (LLMUnavailableError, LLMModelNotFoundError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
