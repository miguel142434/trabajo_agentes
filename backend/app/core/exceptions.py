"""Excepciones de dominio y handler global para FastAPI."""

from __future__ import annotations

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.services.llm_service import (
    LLMError,
    LLMModelNotFoundError,
    LLMTimeoutError,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Excepción base de aplicación
# ---------------------------------------------------------------------------


class AppError(Exception):
    """Excepción base para errores controlados de la aplicación."""

    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Recurso no encontrado.") -> None:
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class BadRequestError(AppError):
    def __init__(self, message: str = "Petición incorrecta.") -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("AppError [%s]: %s", request.url.path, exc.message)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def llm_timeout_handler(request: Request, exc: LLMTimeoutError) -> JSONResponse:
    logger.error("LLMTimeoutError [%s]: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={"detail": str(exc)},
    )


async def llm_unavailable_handler(request: Request, exc: LLMUnavailableError) -> JSONResponse:
    logger.error("LLMUnavailableError [%s]: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


async def llm_model_not_found_handler(request: Request, exc: LLMModelNotFoundError) -> JSONResponse:
    logger.error("LLMModelNotFoundError [%s]: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    logger.error("LLMError [%s]: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": str(exc)},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error inesperado en %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor."},
    )


# ---------------------------------------------------------------------------
# Registro centralizado de handlers
# ---------------------------------------------------------------------------


def register_exception_handlers(app) -> None:  # noqa: ANN001
    """Registra todos los handlers en la instancia de FastAPI."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(LLMTimeoutError, llm_timeout_handler)
    app.add_exception_handler(LLMUnavailableError, llm_unavailable_handler)
    app.add_exception_handler(LLMModelNotFoundError, llm_model_not_found_handler)
    app.add_exception_handler(LLMError, llm_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
