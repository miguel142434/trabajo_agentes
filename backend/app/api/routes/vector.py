from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.vector import VectorAddRequest, VectorAddResponse, VectorSearchRequest, VectorSearchResponse
from app.services.vector_service import VectorService, get_vector_service
from app.core.security import get_current_user

router = APIRouter(prefix="/vector", tags=["Vector"])
Service = Annotated[VectorService, Depends(get_vector_service)]


@router.post("/test-add", response_model=VectorAddResponse, status_code=201)
async def test_add(body: VectorAddRequest, service: Service, user_id: str = Depends(get_current_user)):
    return await service.add(body, user_id=user_id)


@router.post("/test-search", response_model=VectorSearchResponse)
async def test_search(body: VectorSearchRequest, service: Service, user_id: str = Depends(get_current_user)):
    return await service.search(body, user_id=user_id)
