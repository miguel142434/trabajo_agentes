from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.vector import VectorAddRequest, VectorAddResponse, VectorSearchRequest, VectorSearchResponse
from app.services.vector_service import VectorService, get_vector_service

router = APIRouter(prefix="/vector", tags=["Vector"])
Service = Annotated[VectorService, Depends(get_vector_service)]


@router.post("/test-add", response_model=VectorAddResponse, status_code=201)
async def test_add(body: VectorAddRequest, service: Service):
    return await service.add(body)


@router.post("/test-search", response_model=VectorSearchResponse)
async def test_search(body: VectorSearchRequest, service: Service):
    return await service.search(body)
