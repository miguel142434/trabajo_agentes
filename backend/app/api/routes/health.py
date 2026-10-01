"""Endpoint de salud de la aplicación."""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check")
async def health_check() -> dict:
    """Devuelve el estado del servicio.

    Usado por Docker, load balancers y monitorización.
    """
    logger.debug("Health check solicitado.")
    return {"status": "ok"}
